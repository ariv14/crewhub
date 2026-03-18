"""Telegram adapter using Telegram Bot API (webhook mode)."""
import logging
from typing import Optional

import httpx

from gateway.adapters.base import BasePlatformAdapter, NormalizedMessage

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramAdapter(BasePlatformAdapter):
    """Telegram Bot API adapter — webhook-based, no long-polling."""

    def parse_inbound(self, payload: dict) -> Optional[NormalizedMessage]:
        """Parse Telegram webhook update into NormalizedMessage."""
        message = payload.get("message") or payload.get("edited_message")
        if not message:
            return None

        text = message.get("text")
        if not text:
            # v1: text only, skip media
            return None

        from_user = message.get("from", {})
        chat = message.get("chat", {})

        return NormalizedMessage(
            platform_user_id=str(from_user.get("id", "")),
            platform_message_id=str(message.get("message_id", "")),
            chat_id=str(chat.get("id", "")),
            text=text,
        )

    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool:
        """Send message via Telegram Bot API."""
        # Telegram has a 4096 char limit per message
        chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]

        async with httpx.AsyncClient(timeout=15) as client:
            for chunk in chunks:
                resp = await client.post(
                    f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
                )
                if resp.status_code != 200:
                    logger.error("Telegram sendMessage failed: %s %s", resp.status_code, resp.text[:200])
                    # Retry without Markdown parse mode (in case of formatting errors)
                    resp = await client.post(
                        f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": chunk},
                    )
                    if resp.status_code != 200:
                        return False
        return True

    async def send_typing(self, bot_token: str, chat_id: str) -> None:
        """Send typing indicator."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{TELEGRAM_API}/bot{bot_token}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                )
        except Exception:
            pass  # best effort

    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """Register webhook with Telegram via setWebhook API."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "edited_message"],
                    "drop_pending_updates": True,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    logger.info("Telegram webhook registered: %s", webhook_url)
                    return True
            logger.error("Telegram setWebhook failed: %s", resp.text[:200])
            return False

    async def deregister_webhook(self, bot_token: str) -> bool:
        """Remove Telegram webhook."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/deleteWebhook",
            )
            return resp.status_code == 200

    def verify_webhook(self, payload: dict, secret: Optional[str] = None) -> bool:
        """Telegram webhook verification.

        Telegram doesn't sign webhooks by default. If a secret_token was set
        during setWebhook, it's sent in X-Telegram-Bot-Api-Secret-Token header.
        For v1, we rely on the connection_id in the URL being hard to guess (UUID).
        """
        # v1: accept all — URL contains UUID which is hard to guess
        # v2: validate X-Telegram-Bot-Api-Secret-Token header
        return True

    async def get_me(self, bot_token: str) -> dict | None:
        """Get bot info (useful for test endpoint)."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{TELEGRAM_API}/bot{bot_token}/getMe")
            if resp.status_code == 200:
                return resp.json().get("result")
            return None
