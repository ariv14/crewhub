"""Webhook logs API — agent owners can view communication logs for their agents."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import resolve_db_user_id
from src.core.exceptions import ForbiddenError, NotFoundError
from src.database import get_db
from src.models.agent import Agent
from src.models.webhook_log import WebhookLog

router = APIRouter(prefix="/agents/{agent_id}/webhook-logs", tags=["webhook-logs"])


async def _verify_agent_owner(
    agent_id: UUID, owner_id: UUID, db: AsyncSession
) -> Agent:
    """Verify the requesting user owns the agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise NotFoundError(detail=f"Agent {agent_id} not found")
    if agent.owner_id != owner_id:
        raise ForbiddenError(detail="You do not own this agent")
    return agent


@router.get("/")
async def list_webhook_logs(
    agent_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    direction: str | None = Query(None, pattern="^(inbound|outbound)$"),
    method: str | None = Query(None),
    success: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> dict:
    """List webhook logs for an agent (owner only)."""
    await _verify_agent_owner(agent_id, owner_id, db)

    stmt = select(WebhookLog).where(WebhookLog.agent_id == agent_id)

    if direction:
        stmt = stmt.where(WebhookLog.direction == direction)
    if method:
        stmt = stmt.where(WebhookLog.method == method)
    if success is not None:
        stmt = stmt.where(WebhookLog.success == success)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * per_page
    stmt = stmt.order_by(desc(WebhookLog.created_at)).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "agent_id": str(log.agent_id),
                "task_id": str(log.task_id) if log.task_id else None,
                "direction": log.direction,
                "method": log.method,
                "status_code": log.status_code,
                "success": log.success,
                "error_message": log.error_message,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{log_id}")
async def get_webhook_log(
    agent_id: UUID,
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> dict:
    """Get a single webhook log with full request/response (owner only)."""
    await _verify_agent_owner(agent_id, owner_id, db)

    result = await db.execute(
        select(WebhookLog).where(
            WebhookLog.id == log_id,
            WebhookLog.agent_id == agent_id,
        )
    )
    log = result.scalars().first()
    if not log:
        raise NotFoundError(detail=f"Webhook log {log_id} not found")

    return {
        "id": str(log.id),
        "agent_id": str(log.agent_id),
        "task_id": str(log.task_id) if log.task_id else None,
        "direction": log.direction,
        "method": log.method,
        "request_body": log.request_body,
        "response_body": log.response_body,
        "status_code": log.status_code,
        "success": log.success,
        "error_message": log.error_message,
        "latency_ms": log.latency_ms,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
