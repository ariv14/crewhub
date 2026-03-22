# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Telegram webhook handler — runs inside the main backend (no separate gateway needed).

Receives Telegram messages, creates tasks, sends agent responses back.
Eliminates network calls between gateway and backend.
"""
import asyncio
import hashlib
import hmac as hmac_mod
import logging
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.core.encryption import decrypt_value
from src.database import async_session
from src.models.channel import ChannelConnection, ChannelMessage, ChannelContactBlock

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram-webhook"])

# In-memory rate limiter + dedup (same as gateway)
_rate_counters: dict[str, list[float]] = {}
_dedup_seen: dict[str, float] = {}


def _is_rate_limited(key: str, max_req: int = 10, window: int = 60) -> bool:
    now = time.time()
    hits = [t for t in _rate_counters.get(key, []) if t > now - window]
    hits.append(now)
    _rate_counters[key] = hits
    return len(hits) > max_req


def _is_duplicate(conn_id: str, msg_id: str, ttl: int = 300) -> bool:
    key = f"{conn_id}:{msg_id}"
    now = time.time()
    if key in _dedup_seen and now - _dedup_seen[key] < ttl:
        return True
    _dedup_seen[key] = now
    # Cleanup
    if len(_dedup_seen) > 10000:
        _dedup_seen.clear()
    return False


def _pseudonymize(user_id: str, conn_id: str) -> str:
    key = f"{settings.gateway_service_key}:{conn_id}".encode()
    return hmac_mod.new(key, user_id.encode(), hashlib.sha256).hexdigest()[:16]


def _verify_secret(conn_id: str, headers: dict) -> bool:
    if not settings.gateway_service_key:
        return True  # no key configured
    expected = hashlib.sha256(
        f"{settings.gateway_service_key}:{conn_id}".encode()
    ).hexdigest()[:32]
    actual = headers.get("x-telegram-bot-api-secret-token", "")
    if not actual:
        return False
    return hmac_mod.compare_digest(actual, expected)


async def _send_telegram(token: str, chat_id: str, text: str) -> bool:
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for chunk in chunks:
                resp = await client.post(url, json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"})
                if resp.status_code != 200:
                    await client.post(url, json={"chat_id": chat_id, "text": chunk})
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


async def _send_typing(token: str, chat_id: str):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
    except Exception:
        pass


@router.post("/webhook/telegram/{connection_id}")
async def telegram_webhook(connection_id: str, request: Request):
    """Receive Telegram webhook — ack immediately, process in background."""
    import json as json_mod

    body_bytes = await request.body()
    try:
        body = json_mod.loads(body_bytes)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    # Verify webhook secret
    headers = {k.lower(): v for k, v in request.headers.items()}
    if not _verify_secret(connection_id, headers):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized", "debug": "secret_mismatch"})

    # Parse message
    message = body.get("message") or body.get("edited_message")
    if not message or not message.get("text"):
        return {"ok": True, "debug": "no_text_message", "keys": list(body.keys())}

    platform_user_id = str(message["from"]["id"])
    platform_msg_id = str(message["message_id"])
    chat_id = str(message["chat"]["id"])
    text = message["text"]

    # Dedup
    if _is_duplicate(connection_id, platform_msg_id):
        return {"ok": True}

    # Rate limit
    if _is_rate_limited(f"{connection_id}:{platform_user_id}"):
        return {"ok": True}

    # Process synchronously for debugging
    try:
        result = await _process_telegram_message(
            connection_id, platform_user_id, platform_msg_id, chat_id, text
        )
        return {"ok": True, "debug": result, "parsed": {"user": platform_user_id, "msg_id": platform_msg_id, "text": text[:50]}}
    except Exception as e:
        logger.exception("Webhook processing failed: %s", e)
        return {"ok": True, "debug_error": f"{type(e).__name__}: {e}"}


async def _process_telegram_message(
    connection_id: str, platform_user_id: str, platform_msg_id: str, chat_id: str, text: str
):
    """Process Telegram message: look up connection, charge credits, create task, send response."""
    debug_info = {"stage": "start"}
    try:
        async with async_session() as db:
            debug_info["stage"] = "db_connected"
            # Get connection (cast string to UUID)
            from uuid import UUID as _UUID
            try:
                conn_uuid = _UUID(connection_id)
            except ValueError:
                debug_info["stage"] = "invalid_uuid"
                return debug_info
            result = await db.execute(
                select(ChannelConnection).where(ChannelConnection.id == conn_uuid)
            )
            conn = result.scalar_one_or_none()
            if not conn or conn.status != "active":
                debug_info["stage"] = "connection_not_found"
                return debug_info

            debug_info["stage"] = "connection_found"
            debug_info["conn_status"] = conn.status

            # Decrypt bot token
            bot_token = decrypt_value(conn.bot_token) if conn.bot_token else ""
            if not bot_token:
                debug_info["stage"] = "no_bot_token"
                return debug_info
            debug_info["stage"] = "token_decrypted"

            # Check if user is blocked
            user_hash = _pseudonymize(platform_user_id, connection_id)
            blocked = await db.execute(
                select(ChannelContactBlock).where(
                    ChannelContactBlock.connection_id == conn.id,
                    ChannelContactBlock.platform_user_id_hash == user_hash,
                )
            )
            if blocked.scalar_one_or_none():
                return  # silently drop

            # Send typing indicator
            await _send_typing(bot_token, chat_id)

            # Check daily credit limit
            if conn.daily_credit_limit:
                from datetime import datetime, timezone
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                usage_result = await db.execute(
                    select(func.coalesce(func.sum(ChannelMessage.credits_charged), 0))
                    .where(ChannelMessage.connection_id == conn.id)
                    .where(ChannelMessage.created_at >= today)
                )
                today_usage = float(usage_result.scalar_one())
                if today_usage >= conn.daily_credit_limit:
                    await _send_telegram(bot_token, chat_id, "Daily message limit reached. Service will resume tomorrow.")
                    return

            # Check credit balance
            from src.models.user import User
            owner = await db.get(User, conn.owner_id)
            if not owner or not owner.account:
                await _send_telegram(bot_token, chat_id, "Service temporarily unavailable.")
                return

            balance = float(owner.account.balance)
            if balance < 1:
                await _send_telegram(bot_token, chat_id, "Service temporarily unavailable.")
                return

            # Log inbound message (text = NULL for privacy)
            inbound_msg = ChannelMessage(
                connection_id=conn.id,
                platform_user_id_hash=user_hash,
                platform_message_id=platform_msg_id,
                platform_chat_id=chat_id,
                direction="inbound",
                message_text=None,  # GDPR: don't store inbound text
                media_type="text",
            )
            db.add(inbound_msg)
            try:
                await db.flush()
            except IntegrityError:
                await db.rollback()
                return  # duplicate

            # Create task for the agent
            from src.services.task_broker import TaskBrokerService
            broker = TaskBrokerService(db)
            try:
                task = await broker.create_task(
                    provider_agent_id=conn.agent_id,
                    skill_id=conn.skill_id,
                    message=text,
                    creator_user_id=conn.owner_id,
                )
                await db.flush()
                logger.info("Task %s created for Telegram message on connection %s", task.id, connection_id)
            except Exception as e:
                logger.error("Task creation failed: %s", e)
                await _send_telegram(bot_token, chat_id, "Sorry, I couldn't process your request. Please try again.")
                return

            # Wait for task completion (poll with timeout)
            # The task broker dispatches to the agent asynchronously.
            # We poll the task status for up to 120 seconds.
            import asyncio as aio
            from src.models.task import Task
            task_id = task.id
            response_text = None
            start = time.time()

            while time.time() - start < 120:
                await aio.sleep(3)
                async with async_session() as poll_db:
                    t = await poll_db.get(Task, task_id)
                    if not t:
                        break
                    status = t.status.value if hasattr(t.status, "value") else t.status
                    if status == "completed":
                        # Get response from artifacts
                        if t.artifacts:
                            for artifact in t.artifacts:
                                parts = artifact.get("parts", []) if isinstance(artifact, dict) else []
                                for part in parts:
                                    if isinstance(part, dict) and part.get("type") == "text" and part.get("content"):
                                        response_text = part["content"]
                                        break
                                if response_text:
                                    break
                        if not response_text:
                            response_text = "Task completed successfully."
                        break
                    elif status in ("failed", "canceled"):
                        response_text = "Sorry, I couldn't complete your request."
                        break

            if not response_text:
                response_text = "Request is taking longer than expected. Please try again."

            # Send response to Telegram
            success = await _send_telegram(bot_token, chat_id, response_text)

            # Log outbound message (encrypted)
            from src.core.message_crypto import decrypt_message  # noqa: F811
            # We encrypt before storing
            encrypted_text = None
            if response_text:
                from demo_agents.gateway.message_crypto import encrypt_message
                try:
                    encrypted_text = encrypt_message(response_text[:2000])
                except Exception:
                    encrypted_text = response_text[:2000]  # fallback: store plaintext if crypto fails

            outbound_msg = ChannelMessage(
                connection_id=conn.id,
                platform_user_id_hash="agent",
                platform_message_id=f"reply-{platform_msg_id}",
                platform_chat_id=chat_id,
                direction="outbound",
                message_text=encrypted_text,
                task_id=task_id,
                credits_charged=1,  # 1 credit per message
            )
            db.add(outbound_msg)

            # Deduct 1 credit from owner's balance
            from decimal import Decimal
            if owner.account:
                owner.account.balance -= Decimal("1")
                outbound_msg.credits_charged = 1

            await db.commit()
            logger.info("Telegram response sent for connection %s: %s", connection_id, "success" if success else "failed")

    except Exception as e:
        logger.exception("Error processing Telegram message for %s: %s", connection_id, e)
        debug_info["error"] = f"{type(e).__name__}: {e}"
    return debug_info
