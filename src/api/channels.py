# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Channel API routes — CRUD for multi-channel gateway connections."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import resolve_db_user_id
from src.database import get_db
from src.schemas.channel import (
    ChannelAnalytics,
    ChannelCreate,
    ChannelListResponse,
    ChannelResponse,
    ChannelTestResult,
    ChannelUpdate,
)
from src.services.channel_service import ChannelService

router = APIRouter(prefix="/channels", tags=["channels"])


@router.post("/validate-token")
async def validate_token(
    data: ChannelCreate,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Validate platform credentials without creating a channel."""
    service = ChannelService(db)
    result = await service._validate_token(data.platform, data.credentials)
    return {
        "valid": True,
        "platform_bot_id": result.get("platform_bot_id"),
        "bot_name": result.get("bot_name"),
    }


@router.post("/", response_model=ChannelResponse, status_code=201)
async def create_channel(
    data: ChannelCreate,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    ch = await service.create_channel(data, owner_id)
    await db.commit()
    stats = await service._get_today_stats(ch.id)
    return {**ch.__dict__, **stats}


@router.get("/", response_model=ChannelListResponse)
async def list_channels(
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    enriched, total = await service.list_channels(owner_id)
    channels = [{**ch.__dict__, **stats} for ch, stats in enriched]
    return {"channels": channels, "total": total}


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: UUID,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    ch, stats = await service.get_channel(channel_id, owner_id)
    return {**ch.__dict__, **stats}


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: UUID,
    data: ChannelUpdate,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    ch = await service.update_channel(channel_id, owner_id, data)
    await db.commit()
    stats = await service._get_today_stats(ch.id)
    return {**ch.__dict__, **stats}


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: UUID,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    await service.delete_channel(channel_id, owner_id)
    await db.commit()


@router.get("/{channel_id}/analytics", response_model=ChannelAnalytics)
async def get_analytics(
    channel_id: UUID,
    days: int = Query(7, ge=1, le=90),
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    return await service.get_analytics(channel_id, owner_id, days)


@router.post("/{channel_id}/rotate-token", response_model=ChannelResponse)
async def rotate_channel_token(
    channel_id: UUID,
    credentials: dict,
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Rotate bot token for an existing channel connection."""
    service = ChannelService(db)
    conn = await service.rotate_token(channel_id, user_id, credentials)
    await db.commit()
    stats = await service._get_today_stats(conn.id)
    return ChannelResponse.model_validate({**conn.__dict__, **stats})


@router.post("/{channel_id}/test", response_model=ChannelTestResult)
async def test_channel(
    channel_id: UUID,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Placeholder — gateway not deployed in Phase 1
    return {
        "success": False,
        "message": "Gateway not yet deployed. Channel is registered and pending.",
    }
