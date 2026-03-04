"""Live activity feed via Server-Sent Events."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.future import select

from src.core.auth import get_current_user
from src.database import async_session
from src.models.agent import Agent
from src.models.task import Task
from src.models.transaction import Transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])

SSE_POLL_INTERVAL = 2  # seconds
SSE_MAX_DURATION = 300  # 5 minutes


@router.get("/stream")
async def activity_stream(
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream platform activity events via SSE.

    Requires Bearer token in the Authorization header.
    For browser EventSource clients that cannot set headers,
    use a polyfill library like event-source-polyfill or
    fetch-event-source which supports custom headers.

    Emits events for new tasks, completed tasks, failed tasks,
    new agent registrations, and credit transactions.
    """

    async def event_stream():
        last_seen: dict[str, datetime] = {}
        elapsed = 0
        lookback = timedelta(minutes=5)

        while elapsed < SSE_MAX_DURATION:
            try:
                async with async_session() as db:
                    now = datetime.now(timezone.utc)
                    since = now - lookback

                    # New tasks
                    task_since = last_seen.get("task", since)
                    stmt = (
                        select(Task)
                        .where(Task.created_at > task_since)
                        .order_by(desc(Task.created_at))
                        .limit(10)
                    )
                    result = await db.execute(stmt)
                    tasks = result.scalars().all()
                    for task in reversed(tasks):
                        status = task.status.value if hasattr(task.status, "value") else task.status
                        if status == "completed":
                            event_type = "task_completed"
                        elif status == "failed":
                            event_type = "task_failed"
                        else:
                            event_type = "task_created"
                        event = {
                            "type": event_type,
                            "task_id": str(task.id),
                            "status": status,
                            "provider_agent_id": str(task.provider_agent_id) if task.provider_agent_id else None,
                            "created_at": task.created_at.isoformat(),
                        }
                        yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
                        if not last_seen.get("task") or task.created_at > last_seen["task"]:
                            last_seen["task"] = task.created_at

                    # New agents
                    agent_since = last_seen.get("agent", since)
                    stmt = (
                        select(Agent)
                        .where(Agent.created_at > agent_since)
                        .order_by(desc(Agent.created_at))
                        .limit(5)
                    )
                    result = await db.execute(stmt)
                    agents = result.scalars().all()
                    for agent in reversed(agents):
                        event = {
                            "type": "agent_registered",
                            "agent_id": str(agent.id),
                            "name": agent.name,
                            "category": agent.category,
                            "created_at": agent.created_at.isoformat(),
                        }
                        yield f"event: agent_registered\ndata: {json.dumps(event)}\n\n"
                        if not last_seen.get("agent") or agent.created_at > last_seen["agent"]:
                            last_seen["agent"] = agent.created_at

                    # Credit transactions
                    tx_since = last_seen.get("tx", since)
                    stmt = (
                        select(Transaction)
                        .where(Transaction.created_at > tx_since)
                        .order_by(desc(Transaction.created_at))
                        .limit(5)
                    )
                    result = await db.execute(stmt)
                    txns = result.scalars().all()
                    for tx in reversed(txns):
                        tx_type_val = tx.type.value if hasattr(tx.type, "value") else tx.type
                        event = {
                            "type": "credit_transaction",
                            "transaction_id": str(tx.id),
                            "tx_type": tx_type_val,
                            "amount": str(tx.amount),
                            "created_at": tx.created_at.isoformat(),
                        }
                        yield f"event: credit_transaction\ndata: {json.dumps(event)}\n\n"
                        if not last_seen.get("tx") or tx.created_at > last_seen["tx"]:
                            last_seen["tx"] = tx.created_at

            except Exception:
                logger.exception("Activity stream error")
                yield f"event: error\ndata: {json.dumps({'message': 'Internal error'})}\n\n"
                return

            # After first poll, only look at new data
            lookback = timedelta(seconds=SSE_POLL_INTERVAL + 1)
            await asyncio.sleep(SSE_POLL_INTERVAL)
            elapsed += SSE_POLL_INTERVAL

        yield f"event: timeout\ndata: {json.dumps({'message': 'Stream max duration reached'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
