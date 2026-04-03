# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Task lifecycle endpoints: creation, messaging, cancellation, and rating."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from src.config import settings as app_settings
from src.core.auth import resolve_db_user_id
from src.core.exceptions import PaymentVerificationError
from src.core.rate_limiter import rate_limit_dependency
from src.database import get_db
from src.models.task import TaskStatus as TaskStatusModel
from src.models.transaction import Transaction, TransactionType
from src.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskMessage,
    TaskRating,
    TaskResponse,
)
from src.schemas.x402 import X402ReceiptResponse, X402ReceiptSubmit
from src.services.task_broker import TaskBrokerService
from src.services.x402 import X402PaymentService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _enrich_task(task) -> TaskResponse:
    """Build TaskResponse with provider agent name and skill name."""
    resp = TaskResponse.model_validate(task)
    if hasattr(task, "provider_agent") and task.provider_agent:
        resp.provider_agent_name = task.provider_agent.name
    elif task.provider_agent_id is None:
        resp.provider_agent_name = "Deleted Agent"
    if hasattr(task, "skill") and task.skill:
        resp.skill_name = task.skill.name
    return resp


@router.post("/", response_model=TaskResponse, status_code=201,
               dependencies=[Depends(rate_limit_dependency)])
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskResponse:
    """Create a new task for a provider agent.

    Reserves the estimated credits from the caller's account and dispatches
    the task to the target provider agent via the A2A protocol.

    If ``validate_match`` is true, checks message-skill alignment and
    includes a ``delegation_warning`` in the response if mismatched.
    """
    service = TaskBrokerService(db)
    task = await service.create_task(data=data, user_id=user_id)

    response = _enrich_task(task)

    if data.validate_match:
        warning = await service.check_skill_mismatch(
            messages=data.messages,
            skill_id=data.skill_id,
            agent_id=data.provider_agent_id,
        )
        if warning:
            response.delegation_warning = warning

    return response


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskResponse:
    """Get the current status and details of a task."""
    service = TaskBrokerService(db)
    task = await service.get_task(task_id=task_id, user_id=user_id)
    return task


@router.post("/{task_id}/messages", response_model=TaskResponse)
async def send_message(
    task_id: UUID,
    data: TaskMessage,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskResponse:
    """Send a follow-up message to an in-progress task.

    Used when the provider agent requests additional input
    (``input_required`` status).
    """
    service = TaskBrokerService(db)
    task = await service.send_message(
        task_id=task_id,
        message=data,
        user_id=user_id,
    )
    return task


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskResponse:
    """Cancel a task that is still in progress.

    Any reserved credits are released back to the caller's account.
    """
    service = TaskBrokerService(db)
    task = await service.cancel_task(task_id=task_id, user_id=user_id)
    return task


@router.post("/{task_id}/confirm", response_model=TaskResponse)
async def confirm_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskResponse:
    """Confirm a high-cost task that requires approval.

    Reserves credits and dispatches the task to the provider agent.
    Only works on tasks with ``pending_approval`` status.
    """
    service = TaskBrokerService(db)
    task = await service.confirm_task(task_id=task_id, user_id=user_id)
    return _enrich_task(task)


@router.post("/{task_id}/rate", response_model=TaskResponse)
async def rate_task(
    task_id: UUID,
    data: TaskRating,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskResponse:
    """Rate a completed task.

    Only the task creator can submit a rating. The rating contributes to the
    provider agent's reputation score.
    """
    service = TaskBrokerService(db)
    task = await service.rate_task(
        task_id=task_id,
        user_id=user_id,
        rating=data,
    )
    return task


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    agent_id: UUID | None = Query(None, description="Filter by agent ID"),
    status: str | None = Query(None, description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TaskListResponse:
    """List tasks with optional filters.

    Requires authentication. Returns tasks where the current user is
    either the client or the provider agent owner.
    """
    service = TaskBrokerService(db)
    tasks, total = await service.list_tasks(
        user_id=user_id,
        agent_id=agent_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return TaskListResponse(tasks=[_enrich_task(t) for t in tasks], total=total)


@router.post("/{task_id}/x402-receipt", response_model=X402ReceiptResponse)
async def submit_x402_receipt(
    task_id: UUID,
    receipt: X402ReceiptSubmit,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> X402ReceiptResponse:
    """Submit an x402 payment receipt for a pending_payment task."""
    broker = TaskBrokerService(db)
    task = await broker.get_task(task_id, user_id=user_id)

    if task.status != TaskStatusModel.PENDING_PAYMENT:
        raise PaymentVerificationError(
            detail=f"Task is not awaiting payment (status: {task.status.value})"
        )

    if task.payment_method != "x402":
        raise PaymentVerificationError(detail="Task does not use x402 payment method")

    # Check receipt timeout
    from datetime import datetime, timezone
    created = task.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - created).total_seconds() / 60
    if elapsed > app_settings.x402_receipt_timeout_minutes:
        raise PaymentVerificationError(
            detail=f"Receipt submission timeout ({app_settings.x402_receipt_timeout_minutes} min)"
        )

    x402_svc = X402PaymentService(db)

    if await x402_svc.check_replay(receipt.tx_hash):
        raise PaymentVerificationError(detail="Transaction hash already used (replay)")

    required_amount = float(task.credits_quoted or 0)
    errors = x402_svc.validate_receipt(receipt, required_amount=required_amount)
    if errors:
        raise PaymentVerificationError(detail="; ".join(errors))

    verified = await x402_svc.verify_with_facilitator(receipt)
    if not verified:
        raise PaymentVerificationError(detail="Facilitator could not verify payment")

    try:
        await x402_svc.record_receipt(task_id=task.id, receipt=receipt)
    except IntegrityError:
        await db.rollback()
        raise PaymentVerificationError(detail="Transaction hash already used (replay)")

    # Create audit transaction for x402 payment
    audit_txn = Transaction(
        type=TransactionType.X402_PAYMENT,
        amount=Decimal(str(receipt.amount)),
        description=f"x402 payment verified: {receipt.tx_hash}",
    )
    db.add(audit_txn)

    task.status = TaskStatusModel.SUBMITTED
    task.x402_receipt = {
        "tx_hash": receipt.tx_hash,
        "chain": receipt.chain,
        "token": receipt.token,
        "amount": receipt.amount,
        "payer": receipt.payer,
        "payee": receipt.payee,
    }
    await db.commit()

    return X402ReceiptResponse(
        verified=True,
        tx_hash=receipt.tx_hash,
        task_status="submitted",
    )


# ---------------------------------------------------------------------------
# AG-UI: Task streaming endpoint
# ---------------------------------------------------------------------------

_stream_logger = logging.getLogger(__name__ + ".stream")

_STREAM_TERMINAL = {"completed", "failed", "canceled", "rejected"}
_STREAM_POLL_INTERVAL = 2  # seconds — fallback poll interval
_STREAM_MAX_DURATION = 300  # 5 minutes max


@router.get("/{task_id}/stream")
async def stream_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> StreamingResponse:
    """Stream real-time task execution updates via Server-Sent Events.

    If the provider agent supports AG-UI streaming (``capabilities.streaming``),
    relays the agent's SSE stream directly to the client for token-by-token output.

    Otherwise, falls back to polling the task status every 2 seconds and emitting
    status/artifact/done events — same contract, just with latency.

    Events emitted:
      - ``status``   — task status change (includes ``final`` flag)
      - ``text``     — partial text chunk from streaming agent
      - ``thinking`` — agent reasoning (shown collapsed in UI)
      - ``artifact`` — complete artifact
      - ``done``     — final task state with all artifacts
      - ``error``    — error message
    """
    # Validate ownership
    service = TaskBrokerService(db)
    task = await service.get_task(task_id=task_id, user_id=user_id)

    # Check if provider agent supports streaming
    agent_supports_streaming = False
    agent_endpoint = None
    skill_key = None
    if task.provider_agent:
        caps = task.provider_agent.capabilities or {}
        agent_supports_streaming = caps.get("streaming", False)
        agent_endpoint = task.provider_agent.endpoint
    if task.skill:
        skill_key = task.skill.skill_key

    # Resolve MCP context BEFORE entering the generator (db session is still alive here)
    mcp_context = await TaskBrokerService._resolve_mcp_context(
        db, task_id, task.provider_agent_id,
    )

    async def _relay_agent_stream():
        """Connect to agent's SSE and relay chunks to the browser."""
        import httpx

        try:
            params = {
                "id": str(task_id),
                "skill_id": skill_key,
                "messages": task.messages or [],
            }
            if mcp_context:
                params["mcp_context"] = mcp_context

            payload = {
                "jsonrpc": "2.0",
                "id": str(task_id),
                "method": "tasks/sendSubscribe",
                "params": params,
            }
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
            ) as client:
                async with client.stream(
                    "POST",
                    agent_endpoint.rstrip("/") + "/",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                ) as response:
                    response.raise_for_status()
                    done_artifacts = None
                    async for line in response.aiter_lines():
                        # Parse data lines to intercept done events
                        if line.startswith("data:"):
                            try:
                                data = json.loads(line[5:].strip())
                                if data.get("type") == "done":
                                    # Capture artifacts but don't relay agent's done — we emit our own
                                    done_artifacts = data.get("artifacts", [])
                                    continue
                            except (json.JSONDecodeError, KeyError):
                                pass

                        # Relay all other SSE lines to browser
                        if line.startswith("event:"):
                            # Skip the "event: done" line (we'll emit our own)
                            if "done" in line:
                                continue
                            yield line + "\n"
                        elif line.startswith("data:"):
                            yield line + "\n"
                        elif line == "":
                            yield "\n"

                    # Stream finished — finalize task in DB and emit enriched done
                    if done_artifacts:
                        await _finalize_task(task_id, done_artifacts)
                        enriched_done = {
                            "type": "done",
                            "artifacts": done_artifacts,
                            "metadata": {
                                "credits_quoted": float(task.credits_quoted) if task.credits_quoted else 0,
                            },
                        }
                        yield f"event: done\ndata: {json.dumps(enriched_done)}\n\n"

        except Exception as exc:
            _stream_logger.warning("Agent stream relay failed for task %s: %s", task_id, exc)
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Agent stream unavailable, falling back to polling'})}\n\n"
            # Fall back to polling
            async for event in _poll_task_status():
                yield event

    async def _poll_task_status():
        """Fallback: poll task DB and emit SSE events."""
        from src.database import async_session

        last_status = None
        last_artifact_count = 0
        elapsed = 0

        while elapsed < _STREAM_MAX_DURATION:
            try:
                async with async_session() as poll_db:
                    broker = TaskBrokerService(poll_db)
                    t = await broker.get_task(task_id)

                    current_status = t.status.value if hasattr(t.status, "value") else t.status
                    current_artifacts = t.artifacts or []

                    if current_status != last_status:
                        is_final = current_status in _STREAM_TERMINAL
                        event_data = {
                            "type": "status",
                            "content": current_status,
                            "metadata": {"final": is_final},
                        }
                        yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
                        last_status = current_status

                        if is_final:
                            done_data = {
                                "type": "done",
                                "artifacts": current_artifacts,
                                "metadata": {
                                    "credits_quoted": float(t.credits_quoted) if t.credits_quoted else 0,
                                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                                },
                            }
                            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
                            return

                    if len(current_artifacts) > last_artifact_count:
                        for artifact in current_artifacts[last_artifact_count:]:
                            yield f"event: artifact\ndata: {json.dumps({'type': 'artifact', 'artifact': artifact})}\n\n"
                        last_artifact_count = len(current_artifacts)

            except Exception:
                _stream_logger.exception("SSE poll error for task %s", task_id)
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Internal error'})}\n\n"
                return

            await asyncio.sleep(_STREAM_POLL_INTERVAL)
            elapsed += _STREAM_POLL_INTERVAL

        yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Stream timeout'})}\n\n"

    async def _finalize_task(tid: UUID, artifacts: list):
        """Update task in DB when streaming completes."""
        from src.database import async_session

        try:
            async with async_session() as fin_db:
                broker = TaskBrokerService(fin_db)
                await broker.update_task_status(tid, TaskStatusModel.COMPLETED, artifacts=artifacts)
        except Exception:
            _stream_logger.exception("Failed to finalize streaming task %s", tid)

    # Choose streaming strategy
    status_val = task.status.value if hasattr(task.status, "value") else task.status
    if status_val in _STREAM_TERMINAL:
        # Task already done — emit done event immediately
        async def _done_immediately():
            done_data = {
                "type": "done",
                "artifacts": task.artifacts or [],
                "metadata": {
                    "status": status_val,
                    "credits_quoted": float(task.credits_quoted) if task.credits_quoted else 0,
                },
            }
            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

        generator = _done_immediately()
    elif agent_supports_streaming and agent_endpoint:
        generator = _relay_agent_stream()
    else:
        generator = _poll_task_status()

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
