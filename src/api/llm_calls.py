"""LLM Call Inspector — admin-only endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.admin import require_admin
from src.database import get_db
from src.models.llm_call import LLMCall
from src.models.user import User

router = APIRouter(prefix="/admin/llm-calls", tags=["admin"])


@router.get("/")
async def list_llm_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent_id: UUID | None = Query(None),
    status_code: int | None = Query(None),
    provider: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """List LLM calls with pagination and filters."""
    stmt = select(LLMCall)

    if agent_id:
        stmt = stmt.where(LLMCall.agent_id == agent_id)
    if status_code is not None:
        stmt = stmt.where(LLMCall.status_code == status_code)
    if provider:
        stmt = stmt.where(LLMCall.provider == provider)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * per_page
    stmt = stmt.order_by(desc(LLMCall.created_at)).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    calls = result.scalars().all()

    return {
        "calls": [
            {
                "id": str(c.id),
                "agent_id": str(c.agent_id) if c.agent_id else None,
                "task_id": str(c.task_id) if c.task_id else None,
                "provider": c.provider,
                "model": c.model,
                "status_code": c.status_code,
                "latency_ms": c.latency_ms,
                "tokens_input": c.tokens_input,
                "tokens_output": c.tokens_output,
                "error_message": c.error_message,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in calls
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{call_id}")
async def get_llm_call(
    call_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Get a single LLM call with full request/response."""
    stmt = select(LLMCall).where(LLMCall.id == call_id)
    result = await db.execute(stmt)
    call = result.scalars().first()
    if not call:
        from src.core.exceptions import NotFoundError
        raise NotFoundError(detail=f"LLM call {call_id} not found")

    return {
        "id": str(call.id),
        "agent_id": str(call.agent_id) if call.agent_id else None,
        "task_id": str(call.task_id) if call.task_id else None,
        "provider": call.provider,
        "model": call.model,
        "request_body": call.request_body,
        "response_body": call.response_body,
        "status_code": call.status_code,
        "latency_ms": call.latency_ms,
        "tokens_input": call.tokens_input,
        "tokens_output": call.tokens_output,
        "error_message": call.error_message,
        "created_at": call.created_at.isoformat() if call.created_at else None,
    }
