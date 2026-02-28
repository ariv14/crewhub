"""Agent discovery and search endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.discovery import DiscoveryResponse, SearchQuery
from src.services.discovery import DiscoveryService

router = APIRouter(prefix="/discover", tags=["discovery"])


@router.post("/", response_model=DiscoveryResponse)
async def search_agents(
    data: SearchQuery,
    db: AsyncSession = Depends(get_db),
) -> DiscoveryResponse:
    """Search for agents using keyword, semantic, capability, or intent modes.

    Accepts a ``SearchQuery`` body with filters such as category, tags,
    latency/credit constraints, and desired input/output modes.
    """
    service = DiscoveryService(db)
    result = await service.search(query=data)
    return result


@router.get("/recommend/{agent_id}", response_model=DiscoveryResponse)
async def get_recommendations(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DiscoveryResponse:
    """Get agent recommendations based on a reference agent.

    Returns similar or complementary agents that pair well with the given
    agent for multi-step workflows.
    """
    service = DiscoveryService(db)
    matches = await service.get_recommendations(agent_id=agent_id)
    return DiscoveryResponse(
        matches=matches,
        total_candidates=len(matches),
        query_time_ms=0.0,
    )


@router.get("/categories", response_model=list[dict])
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all agent categories with the number of active agents in each.

    Returns a list of ``{"name": str, "count": int}`` objects.
    """
    service = DiscoveryService(db)
    categories = await service.get_categories()
    return categories


@router.get("/skills/trending", response_model=list[dict])
async def get_trending_skills(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get currently trending skills across the marketplace.

    Returns a list of skill summaries ordered by recent usage volume.
    """
    service = DiscoveryService(db)
    skills = await service.get_trending_skills()
    return skills
