# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Channel service — CRUD and analytics for multi-channel gateway connections."""

import os
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

    async def _validate_token(self, platform: str, credentials: dict) -> dict:
        """Validate bot token by calling platform API. Returns bot info or raises BadRequestError."""
        import httpx

        token = credentials.get("bot_token") or credentials.get("access_token", "")

        try:
            if platform == "telegram":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                    if resp.status_code != 200:
                        raise BadRequestError("Invalid Telegram bot token. Create one via @BotFather on Telegram.")
                    data = resp.json().get("result", {})
                    return {"platform_bot_id": str(data.get("id", "")), "bot_name": data.get("username", "")}

            elif platform == "slack":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://slack.com/api/auth.test",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    data = resp.json()
                    if not data.get("ok"):
                        error = data.get("error", "unknown")
                        if "invalid_auth" in error:
                            raise BadRequestError("Invalid Slack token. Make sure you're using the Bot User OAuth Token (starts with xoxb-).")
                        raise BadRequestError(f"Slack token validation failed: {error}")
                    return {"platform_bot_id": data.get("bot_id", ""), "bot_name": data.get("bot_user_id", "")}

            elif platform == "discord":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        "https://discord.com/api/v10/users/@me",
                        headers={"Authorization": f"Bot {token}"},
                    )
                    if resp.status_code != 200:
                        raise BadRequestError("Invalid Discord bot token. Check your token in the Discord Developer Portal.")
                    data = resp.json()
                    return {"platform_bot_id": data.get("id", ""), "bot_name": data.get("username", "")}

            elif platform == "teams":
                app_id = credentials.get("app_id", "")
                app_password = credentials.get("app_password", "")
                if not app_id or not app_password:
                    raise BadRequestError("Teams requires both App ID and App Password.")
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
                        data={
                            "grant_type": "client_credentials",
                            "client_id": app_id,
                            "client_secret": app_password,
                            "scope": "https://api.botframework.com/.default",
                        },
                    )
                    if resp.status_code != 200:
                        raise BadRequestError("Invalid Teams credentials. Check App ID and App Password in Azure Portal.")
                    return {"platform_bot_id": app_id}

            elif platform == "whatsapp":
                phone_id = credentials.get("phone_number_id", "")
                if not phone_id:
                    raise BadRequestError("WhatsApp requires a Phone Number ID.")
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"https://graph.facebook.com/v21.0/{phone_id}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code != 200:
                        raise BadRequestError("Invalid WhatsApp credentials. Check Phone Number ID and Access Token.")
                    return {"platform_bot_id": phone_id}
        except BadRequestError:
            raise
        except Exception as e:
            raise BadRequestError(f"Token validation failed: {str(e)}")

        return {}

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
        credentials = data.credentials
        bot_token = credentials.get("bot_token") or credentials.get("access_token", "")
        if not bot_token:
            raise BadRequestError("Bot token is required")

        # Validate token against platform API before saving
        validation = await self._validate_token(data.platform, credentials)
        platform_bot_id = validation.get("platform_bot_id", "")
        validated_bot_name = validation.get("bot_name")

        # Build webhook_secret from platform-specific fields
        webhook_secret = credentials.get("signing_secret") or credentials.get("verify_token")

        ch = ChannelConnection(
            owner_id=owner_id,
            platform=data.platform,
            bot_token=encrypt_value(bot_token),
            webhook_secret=encrypt_value(webhook_secret) if webhook_secret else None,
            bot_name=validated_bot_name or data.bot_name,
            platform_bot_id=platform_bot_id,
            agent_id=data.agent_id,
            skill_id=data.skill_id,
            status="pending",
            daily_credit_limit=data.daily_credit_limit,
            low_balance_threshold=data.low_balance_threshold,
            pause_on_limit=data.pause_on_limit,
            config={
                k: v
                for k, v in credentials.items()
                if k not in ("bot_token", "access_token", "signing_secret", "verify_token")
            },
        )
        self.db.add(ch)
        await self.db.flush()

        # Generate webhook URL
        gateway_url = os.environ.get("GATEWAY_URL", "https://arimatch1-crewhub-gateway.hf.space")
        webhook_url = f"{gateway_url}/webhook/{data.platform}/{str(ch.id)}"
        ch.webhook_url = webhook_url

        # For auto-managed platforms (Telegram), register webhook
        if data.platform in ("telegram",):
            import httpx

            bot_token_raw = credentials.get("bot_token", "")
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{bot_token_raw}/setWebhook",
                    json={
                        "url": webhook_url,
                        "allowed_updates": ["message", "edited_message"],
                        "drop_pending_updates": True,
                    },
                )
                if resp.status_code == 200 and resp.json().get("ok"):
                    ch.status = "active"
                else:
                    ch.status = "error"
                    ch.error_message = "Failed to register Telegram webhook"
        else:
            # Manual platforms: stay pending until webhook is verified
            ch.status = "pending"

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

    async def rotate_token(self, connection_id: uuid.UUID, owner_id: uuid.UUID, credentials: dict) -> ChannelConnection:
        """Rotate bot token for an existing channel. Validates new token against platform API."""
        ch = await self._get_or_404(connection_id)
        self._check_ownership(ch, owner_id)

        platform = ch.platform
        bot_token = credentials.get("bot_token", "")
        if not bot_token:
            raise BadRequestError("bot_token is required")

        is_valid = await self._validate_token(platform, credentials)
        if not is_valid:
            raise BadRequestError(f"Invalid {platform} token")

        ch.bot_token = encrypt_value(bot_token)
        if credentials.get("signing_secret"):
            ch.webhook_secret = encrypt_value(credentials["signing_secret"])
        ch.status = "active"
        ch.error_message = None
        await self.db.flush()
        return ch

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
