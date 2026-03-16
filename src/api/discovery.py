# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Agent discovery and search endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.core.encryption import decrypt_value
from src.database import get_db
from src.models.user import User
from src.schemas.discovery import DiscoveryResponse, SearchQuery
from src.services.discovery import DiscoveryService

router = APIRouter(prefix="/discover", tags=["discovery"])


async def _resolve_user_keys(db: AsyncSession, current_user: dict) -> tuple[dict[str, str], str, str]:
    """Resolve decrypted LLM keys, user_id, and account_tier from the current user."""
    user_id = current_user["id"]
    firebase_uid = current_user.get("firebase_uid")

    if firebase_uid:
        result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    else:
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        return {}, str(user_id), "free"

    keys: dict[str, str] = {}
    for provider, encrypted in (user.llm_api_keys or {}).items():
        decrypted = decrypt_value(encrypted)
        if decrypted:
            keys[provider] = decrypted

    return keys, str(user.id), getattr(user, "account_tier", "free")


@router.post("/", response_model=DiscoveryResponse)
async def search_agents(
    data: SearchQuery,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> DiscoveryResponse:
    """Search for agents using keyword, semantic, capability, or intent modes.

    Accepts a ``SearchQuery`` body with filters such as category, tags,
    latency/credit constraints, and desired input/output modes.
    """
    user_keys, user_id, account_tier = await _resolve_user_keys(db, current_user)
    service = DiscoveryService(
        db, user_llm_keys=user_keys, user_id=user_id, account_tier=account_tier,
    )
    result = await service.search(query=data)
    return result


@router.get("/recommend/{agent_id}", response_model=DiscoveryResponse)
async def get_recommendations(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DiscoveryResponse:
    """Get agent recommendations based on a reference agent (public, no auth required).

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
