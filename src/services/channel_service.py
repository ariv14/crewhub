# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Channel service — CRUD and analytics for multi-channel gateway connections."""

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, delete

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.channel import ChannelConnection, ChannelMessage, ChannelContactBlock
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
        except Exception:
            logger.exception("Token validation error for platform %s", platform)
            raise BadRequestError("Token validation failed. Please check your credentials and try again.")

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
            from src.config import settings as app_settings

            bot_token_raw = credentials.get("bot_token", "")

            # Derive per-connection webhook secret (same logic as gateway/main.py verify_webhook)
            # Telegram will send this as X-Telegram-Bot-Api-Secret-Token on every webhook call
            telegram_secret_token = ""
            if app_settings.gateway_service_key:
                telegram_secret_token = hashlib.sha256(
                    f"{app_settings.gateway_service_key}:{str(ch.id)}".encode()
                ).hexdigest()[:32]

            set_webhook_payload: dict = {
                "url": webhook_url,
                "allowed_updates": ["message", "edited_message"],
                "drop_pending_updates": True,
            }
            if telegram_secret_token:
                set_webhook_payload["secret_token"] = telegram_secret_token

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{bot_token_raw}/setWebhook",
                    json=set_webhook_payload,
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

        # Single batch query for today's stats (avoids N+1)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stats_result = await self.db.execute(
            select(
                ChannelMessage.connection_id,
                func.count().label("messages_today"),
                func.coalesce(func.sum(ChannelMessage.credits_charged), 0).label("credits_today"),
            )
            .where(ChannelMessage.created_at >= today)
            .where(ChannelMessage.connection_id.in_([ch.id for ch in channels]))
            .group_by(ChannelMessage.connection_id)
        )
        stats_map = {
            str(r.connection_id): {"messages_today": r.messages_today, "credits_today": float(r.credits_today)}
            for r in stats_result.all()
        }

        enriched = []
        for ch in channels:
            stats = stats_map.get(str(ch.id), {"messages_today": 0, "credits_today": 0.0})
            enriched.append((ch, stats))
        return enriched, len(channels)

    async def _get_today_stats(self, channel_id: uuid.UUID):
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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

        # Clean up Telegram webhook before deletion
        if ch.platform == "telegram" and ch.bot_token:
            from src.core.encryption import decrypt_value
            import httpx
            try:
                token = decrypt_value(ch.bot_token)
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
            except Exception:
                pass  # best-effort cleanup

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

        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(
                func.date(ChannelMessage.created_at).label("date"),
                func.count().label("messages"),
                func.sum(ChannelMessage.credits_charged).label("credits"),
            )
            .where(ChannelMessage.connection_id == channel_id)
            .where(ChannelMessage.created_at >= cutoff)
            .group_by(func.date(ChannelMessage.created_at))
            .order_by(func.date(ChannelMessage.created_at))
        )
        rows = result.all()
        return {
            "daily": [{"date": str(r.date), "messages": r.messages, "credits": float(r.credits or 0)} for r in rows],
            "total_messages": sum(r.messages for r in rows),
            "total_credits": sum(float(r.credits or 0) for r in rows),
        }

    async def get_contacts(self, connection_id, owner_id, limit=50, offset=0):
        conn = await self.get_channel(connection_id, owner_id)
        if not conn:
            return None

        # Aggregate contacts from messages
        result = await self.db.execute(
            select(
                ChannelMessage.platform_user_id_hash,
                func.count().label("message_count"),
                func.max(ChannelMessage.created_at).label("last_seen"),
                func.min(ChannelMessage.created_at).label("first_seen"),
            )
            .where(ChannelMessage.connection_id == connection_id)
            .group_by(ChannelMessage.platform_user_id_hash)
            .order_by(func.max(ChannelMessage.created_at).desc())
            .limit(limit).offset(offset)
        )
        rows = result.all()

        # Get blocked users
        blocked_result = await self.db.execute(
            select(ChannelContactBlock.platform_user_id_hash)
            .where(ChannelContactBlock.connection_id == connection_id)
        )
        blocked_set = {r[0] for r in blocked_result.all()}

        # Count total unique contacts
        count_result = await self.db.execute(
            select(func.count(func.distinct(ChannelMessage.platform_user_id_hash)))
            .where(ChannelMessage.connection_id == connection_id)
        )
        total = count_result.scalar_one()

        contacts = [{
            "platform_user_id_hash": r.platform_user_id_hash,
            "message_count": r.message_count,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            "first_seen": r.first_seen.isoformat() if r.first_seen else None,
            "is_blocked": r.platform_user_id_hash in blocked_set,
        } for r in rows]

        return {"contacts": contacts, "total": total}

    async def get_channel_messages(self, connection_id, owner_id, direction=None, cursor=None, limit=20):
        conn = await self.get_channel(connection_id, owner_id)
        if not conn:
            return None

        from src.core.message_crypto import decrypt_message

        query = select(ChannelMessage).where(ChannelMessage.connection_id == connection_id)
        if direction:
            query = query.where(ChannelMessage.direction == direction)
        if cursor:
            from datetime import datetime as dt
            query = query.where(ChannelMessage.created_at < dt.fromisoformat(cursor))
        query = query.order_by(ChannelMessage.created_at.desc()).limit(limit + 1)

        result = await self.db.execute(query)
        rows = result.scalars().all()
        has_more = len(rows) > limit
        messages = rows[:limit]

        return {
            "messages": [{
                "id": str(m.id),
                "direction": m.direction,
                "platform_user_id_hash": m.platform_user_id_hash,
                "message_text": decrypt_message(m.message_text) if m.direction == "outbound" else None,
                "credits_charged": float(m.credits_charged),
                "response_time_ms": m.response_time_ms,
                "created_at": m.created_at.isoformat(),
            } for m in messages],
            "cursor": messages[-1].created_at.isoformat() if messages else None,
            "has_more": has_more,
        }

    async def block_contact(self, connection_id, owner_id, user_hash, blocked_by, reason=None):
        conn = await self.get_channel(connection_id, owner_id)
        if not conn:
            return None
        block = ChannelContactBlock(
            connection_id=connection_id, platform_user_id_hash=user_hash,
            blocked_by=blocked_by, reason=reason
        )
        self.db.add(block)
        await self.db.flush()
        return block

    async def unblock_contact(self, connection_id, owner_id, user_hash):
        conn = await self.get_channel(connection_id, owner_id)
        if not conn:
            return None
        await self.db.execute(
            delete(ChannelContactBlock)
            .where(ChannelContactBlock.connection_id == connection_id)
            .where(ChannelContactBlock.platform_user_id_hash == user_hash)
        )
        await self.db.flush()
        return True

    async def delete_contact_data(self, connection_id, owner_id, user_hash):
        """GDPR erasure: delete all messages and block records for a contact."""
        conn = await self.get_channel(connection_id, owner_id)
        if not conn:
            return None
        result = await self.db.execute(
            delete(ChannelMessage)
            .where(ChannelMessage.connection_id == connection_id)
            .where(ChannelMessage.platform_user_id_hash == user_hash)
        )
        # Also remove any block
        await self.db.execute(
            delete(ChannelContactBlock)
            .where(ChannelContactBlock.connection_id == connection_id)
            .where(ChannelContactBlock.platform_user_id_hash == user_hash)
        )
        await self.db.flush()
        return {"deleted_messages": result.rowcount, "user_hash": user_hash, "channel_id": str(connection_id)}
