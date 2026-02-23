"""Health check endpoints for the platform and individual agents."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.health_monitor import HealthMonitorService

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic platform health check.

    Returns a simple status indicator and the current API version.
    """
    return {"status": "healthy", "version": "0.1.0"}


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
