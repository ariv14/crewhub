# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Channel API routes — CRUD for multi-channel gateway connections."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.audit import audit_log
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
    await audit_log(db, action="channel.create", actor_user_id=str(owner_id), target_type="channel", target_id=ch.id)
    await db.commit()
    await db.refresh(ch)
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
    await audit_log(db, action="channel.update", actor_user_id=str(owner_id), target_type="channel", target_id=channel_id)
    await db.commit()
    await db.refresh(ch)
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
    await audit_log(db, action="channel.delete", actor_user_id=str(owner_id), target_type="channel", target_id=channel_id)
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
    await audit_log(db, action="channel.rotate_token", actor_user_id=str(user_id), target_type="channel", target_id=channel_id)
    await db.commit()
    await db.refresh(conn)
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


@router.get("/{channel_id}/contacts")
async def get_channel_contacts(
    channel_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    result = await service.get_contacts(channel_id, user_id, limit, offset)
    await audit_log(db, action="channel.view_contacts", actor_user_id=str(user_id), target_type="channel", target_id=channel_id)
    return result


@router.get("/{channel_id}/contacts/{user_hash}/messages")
async def get_contact_messages(
    channel_id: UUID,
    user_hash: str,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    # Filter messages by specific user hash
    result = await service.get_channel_messages(channel_id, user_id, cursor=cursor, limit=limit)
    if result:
        result["messages"] = [m for m in result["messages"] if m["platform_user_id_hash"] == user_hash]
    return result


@router.post("/{channel_id}/contacts/{user_hash}/block")
async def block_contact(
    channel_id: UUID,
    user_hash: str,
    reason: str = "",
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    await service.block_contact(channel_id, user_id, user_hash, user_id, reason or None)
    await audit_log(db, action="channel.block_contact", actor_user_id=str(user_id), target_type="channel_contact", target_id=channel_id, new_value={"user_hash": user_hash, "reason": reason})
    await db.commit()
    return {"status": "blocked", "user_hash": user_hash}


@router.delete("/{channel_id}/contacts/{user_hash}/block")
async def unblock_contact(
    channel_id: UUID,
    user_hash: str,
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    await service.unblock_contact(channel_id, user_id, user_hash)
    await audit_log(db, action="channel.unblock_contact", actor_user_id=str(user_id), target_type="channel_contact", target_id=channel_id, new_value={"user_hash": user_hash})
    await db.commit()
    return {"status": "unblocked", "user_hash": user_hash}


@router.delete("/{channel_id}/contacts/{user_hash}/messages")
async def delete_contact_data(
    channel_id: UUID,
    user_hash: str,
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Article 17 — right to erasure for platform end-users."""
    service = ChannelService(db)
    result = await service.delete_contact_data(channel_id, user_id, user_hash)
    await audit_log(db, action="channel.gdpr_erasure", actor_user_id=str(user_id), target_type="channel_contact", target_id=channel_id, new_value={"user_hash": user_hash, "deleted_messages": result["deleted_messages"]})
    await db.commit()
    return result


@router.get("/{channel_id}/messages")
async def get_channel_messages(
    channel_id: UUID,
    direction: str | None = None,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = ChannelService(db)
    return await service.get_channel_messages(channel_id, user_id, direction, cursor, limit)
