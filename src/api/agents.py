"""Agent registration and management endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete as sa_delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.core.auth import get_current_user
from src.core.config import settings
from src.database import get_db
from src.models.agent import Agent, Skill
from src.models.task import Task
from src.schemas.agent import (
    AgentCardResponse,
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentStatsResponse,
    AgentStatus,
    AgentUpdate,
    DailyTaskCount,
)
from src.services.registry import RegistryService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/", response_model=AgentResponse, status_code=201)
async def register_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AgentResponse:
    """Register a new agent in the marketplace.

    Requires authentication. The caller becomes the agent owner.
    """
    service = RegistryService(db)
    agent = await service.register_agent(owner_id=UUID(current_user["id"]), data=data)
    return agent


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    status: AgentStatus | None = Query(None, description="Filter by status"),
    owner_id: str | None = Query(None, description="Filter by owner user ID"),
    db: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    """List registered agents with optional filters.

    This is a public endpoint and does not require authentication.
    """
    service = RegistryService(db)
    agents, total = await service.list_agents(
        page=page,
        per_page=per_page,
        category=category,
        status=status.value if status else None,
        owner_id=owner_id,
    )
    return AgentListResponse(agents=agents, total=total, page=page, per_page=per_page)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Retrieve the full details of a specific agent.

    This is a public endpoint and does not require authentication.
    """
    service = RegistryService(db)
    agent = await service.get_agent(agent_id=agent_id)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AgentResponse:
    """Update an existing agent's details.

    Requires authentication and ownership of the agent.
    """
    service = RegistryService(db)
    agent = await service.update_agent(
        agent_id=agent_id,
        owner_id=UUID(current_user["id"]),
        data=data,
    )
    return agent


@router.delete("/{agent_id}", response_model=AgentResponse)
async def deactivate_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AgentResponse:
    """Deactivate an agent (soft-delete).

    Requires authentication and ownership of the agent.
    """
    service = RegistryService(db)
    await service.deactivate_agent(
        agent_id=agent_id,
        owner_id=UUID(current_user["id"]),
    )
    agent = await service.get_agent(agent_id=agent_id)
    return agent


@router.get("/{agent_id}/card", response_model=AgentCardResponse)
async def get_agent_card(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentCardResponse:
    """Return the A2A-spec compliant agent card JSON.

    This is a public endpoint and does not require authentication.
    """
    service = RegistryService(db)
    card = await service.get_agent_card(agent_id=agent_id)
    return card


@router.get("/{agent_id}/pricing")
async def get_agent_pricing(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the full pricing and licensing details for an agent.

    Public endpoint. Shows license type, available tiers, quotas, and trial info.
    """
    service = RegistryService(db)
    agent = await service.get_agent(agent_id=agent_id)
    pricing = agent.pricing or {}
    return {
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "license_type": agent.license_type,
        "pricing": pricing,
        "tiers": pricing.get("tiers", []),
        "trial": {
            "days": pricing.get("trial_days"),
            "task_limit": pricing.get("trial_task_limit"),
        } if pricing.get("trial_days") else None,
    }


@router.get("/{agent_id}/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentStatsResponse:
    """Return daily task counts for the last 30 days.

    Public endpoint for sparkline charts on agent cards.
    """
    since = datetime.now(timezone.utc) - timedelta(days=30)
    date_col = func.date(Task.created_at).label("date")
    stmt = (
        select(
            date_col,
            func.count().label("count"),
        )
        .where(Task.provider_agent_id == agent_id)
        .where(Task.created_at >= since)
        .group_by(func.date(Task.created_at))
        .order_by(func.date(Task.created_at))
    )
    result = await db.execute(stmt)
    rows = result.all()
    return AgentStatsResponse(
        daily_tasks=[DailyTaskCount(date=str(r.date), count=r.count) for r in rows]
    )


@router.post("/{agent_id}/verify", response_model=AgentResponse)
async def request_verification(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AgentResponse:
    """Request verification review for an agent.

    Requires authentication and ownership of the agent. Verification is
    processed asynchronously and the agent status will be updated once
    the review is complete.
    """
    service = RegistryService(db)
    await service.request_verification(
        agent_id=agent_id,
        owner_id=UUID(current_user["id"]),
    )
    agent = await service.get_agent(agent_id=agent_id)
    return agent


@router.delete("/admin/purge-inactive")
async def purge_inactive_agents(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Hard-delete all inactive agents. DEBUG mode only."""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not Found")

    # Find inactive agents
    result = await db.execute(
        select(Agent).where(Agent.status == "inactive")
    )
    inactive = result.scalars().all()
    ids = [a.id for a in inactive]
    names = [a.name for a in inactive]

    if not ids:
        return {"deleted": 0, "agents": []}

    # Delete skills first (FK), then agents
    await db.execute(sa_delete(Skill).where(Skill.agent_id.in_(ids)))
    await db.execute(sa_delete(Agent).where(Agent.id.in_(ids)))
    await db.commit()

    return {"deleted": len(ids), "agents": names}
