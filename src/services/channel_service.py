# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Channel service — CRUD and analytics for multi-channel gateway connections."""

import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.channel import ChannelConnection, ChannelMessage
from src.models.agent import Agent
from src.models.skill import AgentSkill
from src.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from src.core.encryption import encrypt_value


class ChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_404(self, channel_id: uuid.UUID) -> ChannelConnection:
        result = await self.db.execute(
            select(ChannelConnection).where(ChannelConnection.id == channel_id)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            raise NotFoundError("Channel not found")
        return ch

    def _check_ownership(self, ch: ChannelConnection, owner_id: uuid.UUID):
        if ch.owner_id != owner_id:
            raise ForbiddenError("You do not own this channel")

    async def create_channel(self, data, owner_id: uuid.UUID) -> ChannelConnection:
        # Verify agent exists and is owned by this developer
        agent = await self.db.get(Agent, data.agent_id)
        if not agent or agent.owner_id != owner_id:
            raise BadRequestError("Agent not found or not owned by you")

        # Verify skill if provided
        if data.skill_id:
            skill = await self.db.get(AgentSkill, data.skill_id)
            if not skill or skill.agent_id != data.agent_id:
                raise BadRequestError("Skill not found on this agent")

        # Encrypt bot token from credentials
        bot_token = data.credentials.get("bot_token") or data.credentials.get("access_token", "")
        if not bot_token:
            raise BadRequestError("Bot token is required")

        # Build webhook_secret from platform-specific fields
        webhook_secret = data.credentials.get("signing_secret") or data.credentials.get("verify_token")

        ch = ChannelConnection(
            owner_id=owner_id,
            platform=data.platform,
            bot_token=encrypt_value(bot_token),
            webhook_secret=encrypt_value(webhook_secret) if webhook_secret else None,
            bot_name=data.bot_name,
            agent_id=data.agent_id,
            skill_id=data.skill_id,
            status="pending",
            daily_credit_limit=data.daily_credit_limit,
            low_balance_threshold=data.low_balance_threshold,
            pause_on_limit=data.pause_on_limit,
            config={
                k: v
                for k, v in data.credentials.items()
                if k not in ("bot_token", "access_token", "signing_secret", "verify_token")
            },
        )
        self.db.add(ch)
        await self.db.flush()
        return ch

    async def list_channels(self, owner_id: uuid.UUID):
        result = await self.db.execute(
            select(ChannelConnection)
            .where(ChannelConnection.owner_id == owner_id)
            .order_by(ChannelConnection.created_at.desc())
        )
        channels = list(result.scalars().all())

        # Compute today's stats for each channel
        enriched = []
        for ch in channels:
            stats = await self._get_today_stats(ch.id)
            enriched.append((ch, stats))
        return enriched, len(channels)

    async def _get_today_stats(self, channel_id: uuid.UUID):
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(
                func.count(ChannelMessage.id),
                func.coalesce(func.sum(ChannelMessage.credits_charged), 0),
            ).where(
                ChannelMessage.connection_id == channel_id,
                ChannelMessage.created_at >= today,
            )
        )
        row = result.one()
        return {"messages_today": row[0], "credits_used_today": row[1]}

    async def get_channel(self, channel_id: uuid.UUID, owner_id: uuid.UUID):
        ch = await self._get_or_404(channel_id)
        self._check_ownership(ch, owner_id)
        stats = await self._get_today_stats(channel_id)
        return ch, stats

    async def update_channel(self, channel_id: uuid.UUID, owner_id: uuid.UUID, data):
        ch = await self._get_or_404(channel_id)
        self._check_ownership(ch, owner_id)

        for field in [
            "bot_name",
            "agent_id",
            "skill_id",
            "daily_credit_limit",
            "low_balance_threshold",
            "pause_on_limit",
            "status",
        ]:
            value = getattr(data, field, None)
            if value is not None:
                setattr(ch, field, value)

        if data.status == "active" and ch.paused_reason:
            ch.paused_reason = None

        await self.db.flush()
        return ch

    async def delete_channel(self, channel_id: uuid.UUID, owner_id: uuid.UUID):
        ch = await self._get_or_404(channel_id)
        self._check_ownership(ch, owner_id)
        await self.db.delete(ch)
        await self.db.flush()

    async def get_analytics(
        self, channel_id: uuid.UUID, owner_id: uuid.UUID, days: int = 7
    ):
        ch = await self._get_or_404(channel_id)
        self._check_ownership(ch, owner_id)
        # Return placeholder analytics — full implementation in Phase 5
        return {
            "channel_id": str(channel_id),
            "period_days": days,
            "daily_messages": [],
            "daily_credits": [],
            "top_users": [],
            "cost_breakdown": {
                "agent_processing": 0,
                "platform_surcharge": 0,
                "total": 0,
                "avg_per_message": 0,
            },
        }
