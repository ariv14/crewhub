"""Health check endpoints for the platform and individual agents."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import engine, get_db
from src.services.health_monitor import HealthMonitorService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Platform health check with database connectivity verification."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "version": "0.1.0"}
    except Exception:
        logger.exception("Health check: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "version": "0.1.0", "detail": "Database unreachable"},
        )


@router.get("/health/agents/{agent_id}")
async def agent_health_check(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check the health of a specific registered agent.

    Pings the agent's endpoint and returns its availability status,
    response latency, and last-seen timestamp.
    """
    service = HealthMonitorService(db)
    result = await service.check_agent_health(agent_id=agent_id)
    return result
