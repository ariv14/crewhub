"""LLM Call logger service for tracking outbound LLM/A2A calls."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_call import LLMCall

logger = logging.getLogger(__name__)


class LLMCallLogger:
    """Logs outbound LLM/A2A calls to the llm_calls table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_call(
        self,
        *,
        provider: str,
        model: str,
        agent_id: UUID | None = None,
        task_id: UUID | None = None,
        request_body: dict | None = None,
        response_body: dict | None = None,
        status_code: int | None = None,
        latency_ms: int | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        error_message: str | None = None,
    ) -> LLMCall:
        """Create an LLM call log entry."""
        call = LLMCall(
            agent_id=agent_id,
            task_id=task_id,
            provider=provider,
            model=model,
            request_body=request_body,
            response_body=response_body,
            status_code=status_code,
            latency_ms=latency_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            error_message=error_message,
        )
        self.db.add(call)
        await self.db.flush()
        return call


async def log_a2a_call(
    db: AsyncSession,
    *,
    agent_id: UUID | None = None,
    task_id: UUID | None = None,
    endpoint: str,
    method: str,
    request_body: dict | None = None,
    response_body: dict | None = None,
    status_code: int | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    """Convenience function to log an A2A gateway call."""
    try:
        llm_logger = LLMCallLogger(db)
        await llm_logger.log_call(
            provider="a2a",
            model=f"{method}@{endpoint[:100]}",
            agent_id=agent_id,
            task_id=task_id,
            request_body=request_body,
            response_body=response_body,
            status_code=status_code,
            latency_ms=latency_ms,
            error_message=error_message,
        )
    except Exception as e:
        logger.warning(f"Failed to log A2A call: {e}")
