# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""API router for community-created custom agents."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user, resolve_db_user_id
from src.database import get_db
from src.schemas.custom_agent import (
    AgentRequestListResponse,
    AgentRequestResponse,
    CreateAgentRequest,
    CreateAgentResponse,
    CustomAgentListResponse,
    CustomAgentResponse,
    TryAgentRequest,
    VoteRequest,
)
from src.services.custom_agent_service import CustomAgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom-agents", tags=["custom-agents"])

_bearer = HTTPBearer(auto_error=False)


def _to_response(agent, user_vote: int | None = None) -> CustomAgentResponse:
    """Convert ORM model to response schema."""
    return CustomAgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        category=agent.category,
        tags=agent.tags or [],
        source_query=agent.source_query,
        status=agent.status,
        try_count=agent.try_count,
        completion_count=agent.completion_count,
        avg_rating=agent.avg_rating,
        upvote_count=agent.upvote_count,
        promoted_agent_id=str(agent.promoted_agent_id) if agent.promoted_agent_id else None,
        created_by_user_id=str(agent.created_by_user_id) if agent.created_by_user_id else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        user_vote=getattr(agent, "_user_vote", user_vote),
    )


async def _optional_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> UUID | None:
    """Resolve authenticated user's DB UUID, or None if unauthenticated."""
    if credentials is None and not x_api_key:
        return None
    try:
        from src.core.auth import get_current_user as _get_user
        user = await _get_user(request=request, credentials=credentials, x_api_key=x_api_key)
        # Resolve to DB UUID
        from sqlalchemy import select as sa_select
        from src.database import async_session
        from src.models.user import User

        async with async_session() as db:
            if "firebase_uid" in user:
                row = (await db.execute(
                    sa_select(User).where(User.firebase_uid == user["firebase_uid"])
                )).scalar_one_or_none()
            else:
                row = (await db.execute(
                    sa_select(User).where(User.id == UUID(user["id"]))
                )).scalar_one_or_none()
            return row.id if row else None
    except Exception:
        return None


@router.post("/create", response_model=CreateAgentResponse, status_code=201)
async def create_custom_agent(
    data: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
):
    """Create a custom agent from a natural-language description."""
    service = CustomAgentService(db)
    result = await service.create_agent(
        query=data.message,
        user_id=user_id,
        category=data.category,
        auto_execute=data.auto_execute,
    )
    return CreateAgentResponse(
        agent=_to_response(result["agent"]),
        task_id=result.get("task_id"),
        task_status="submitted" if result.get("task_id") else None,
        result=result.get("result"),
    )


@router.get("/", response_model=CustomAgentListResponse)
async def list_custom_agents(
    sort: str = Query("popular", pattern="^(popular|tried|rated|new)$"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: UUID | None = Depends(_optional_user_id),
):
    """List community-created agents."""
    service = CustomAgentService(db)
    result = await service.list_agents(
        sort=sort, category=category, page=page, per_page=per_page, user_id=user_id
    )
    return CustomAgentListResponse(
        agents=[_to_response(a) for a in result["agents"]],
        total=result["total"],
    )


@router.get("/{agent_id}", response_model=CustomAgentResponse)
async def get_custom_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID | None = Depends(_optional_user_id),
):
    """Get a custom agent by ID."""
    service = CustomAgentService(db)
    agent = await service.get_agent(agent_id, user_id=user_id)
    return _to_response(agent)


@router.post("/{agent_id}/try", response_model=CreateAgentResponse)
async def try_custom_agent(
    agent_id: UUID,
    data: TryAgentRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
):
    """Run a task using a community-created custom agent."""
    service = CustomAgentService(db)
    result = await service.try_custom_agent(agent_id, data.message, user_id)
    agent = await service.get_agent(agent_id, user_id=user_id)
    return CreateAgentResponse(
        agent=_to_response(agent),
        task_id=result.get("task_id"),
        task_status="submitted" if result.get("task_id") else "completed",
        result=result.get("result"),
    )


@router.post("/{agent_id}/vote", response_model=CustomAgentResponse)
async def vote_custom_agent(
    agent_id: UUID,
    data: VoteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
):
    """Upvote (+1) or downvote (-1) a custom agent."""
    service = CustomAgentService(db)
    agent = await service.vote(agent_id, user_id, data.vote)
    return _to_response(agent)


@router.get("/requests/list", response_model=AgentRequestListResponse)
async def list_agent_requests(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List demand signals (admin only)."""
    from sqlalchemy import select
    from src.core.exceptions import ForbiddenError
    from src.models.user import User

    user = (
        await db.execute(select(User).where(User.id == UUID(current_user["id"])))
    ).scalar_one_or_none()
    if not user or not user.is_admin:
        raise ForbiddenError("Admin access required")

    service = CustomAgentService(db)
    result = await service.list_requests(page=page, per_page=per_page)
    return AgentRequestListResponse(
        requests=[
            AgentRequestResponse(
                id=str(r.id),
                user_id=str(r.user_id) if r.user_id else None,
                query=r.query,
                best_match_confidence=r.best_match_confidence,
                custom_agent_id=str(r.custom_agent_id) if r.custom_agent_id else None,
                created_at=r.created_at,
            )
            for r in result["requests"]
        ],
        total=result["total"],
    )
