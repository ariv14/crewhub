"""Discord adapter using Interactions endpoint (webhook mode, not WebSocket gateway)."""
import logging
from typing import Optional

import httpx

from adapters.base import BasePlatformAdapter, NormalizedMessage

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


class DiscordAdapter(BasePlatformAdapter):
    """Discord Interactions endpoint adapter — webhook-based, no gateway WebSocket."""

    def parse_inbound(self, payload: dict) -> Optional[NormalizedMessage]:
        """Parse Discord interaction or message payload."""
        # Type 1 = PING (verification) — handled separately via handle_ping()
        interaction_type = payload.get("type")
        if interaction_type == 1:
            return None

        # Type 2 = APPLICATION_COMMAND (slash commands)
        # Type 4 = MESSAGE_COMPONENT
        # For now, handle message-like interactions
        data = payload.get("data", {})
        user = payload.get("member", {}).get("user", {}) or payload.get("user", {})

        # Extract text from options or resolved messages
        text = ""
        if data.get("options"):
            # Slash command with text option
            for opt in data["options"]:
                if opt.get("type") == 3:  # STRING type
                    text = opt.get("value", "")
                    break

        if not text:
            # Try to get from resolved messages
            text = data.get("name", "")  # fallback to command name

        if not text:
            return None

        channel_id = payload.get("channel_id", "")

        return NormalizedMessage(
            platform_user_id=user.get("id", ""),
            platform_message_id=payload.get("id", ""),
            chat_id=channel_id,
            text=text,
        )

    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool:
        """Send message via Discord channel messages endpoint."""
        # Chunk to 2000 chars (Discord limit)
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]

        async with httpx.AsyncClient(timeout=15) as client:
            for chunk in chunks:
                resp = await client.post(
                    f"{DISCORD_API}/channels/{chat_id}/messages",
                    json={"content": chunk},
                    headers={"Authorization": f"Bot {bot_token}"},
                )
                if resp.status_code not in (200, 201):
                    logger.error("Discord sendMessage failed: %s %s", resp.status_code, resp.text[:200])
                    return False
        return True

    async def send_followup(self, application_id: str, interaction_token: str, text: str) -> bool:
        """Send followup message for an interaction (used after deferred response)."""
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]

        async with httpx.AsyncClient(timeout=15) as client:
            for chunk in chunks:
                resp = await client.post(
                    f"{DISCORD_API}/webhooks/{application_id}/{interaction_token}",
                    json={"content": chunk},
                )
                if resp.status_code not in (200, 201):
                    logger.error("Discord followup failed: %s", resp.status_code)
                    return False
        return True

    async def send_typing(self, bot_token: str, chat_id: str) -> None:
        """Send typing indicator."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{DISCORD_API}/channels/{chat_id}/typing",
                    headers={"Authorization": f"Bot {bot_token}"},
                )
        except Exception:
            pass  # best effort

    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """Discord interactions URL is set in the Discord Developer Portal.
        Auto-registration via API is possible for guild commands but not the interactions endpoint."""
        logger.info("Discord interactions endpoint must be configured in Developer Portal: %s", webhook_url)
        return True

    async def deregister_webhook(self, bot_token: str) -> bool:
        """No-op — developer removes in Developer Portal."""
        return True

    def verify_webhook(self, payload: dict, secret: Optional[str] = None) -> bool:
        """Verify Discord interaction signature using Ed25519.

        Call with payload containing _signature, _timestamp, and _body keys
        injected by the route handler from request headers/body:
          - _signature: X-Signature-Ed25519 header value
          - _timestamp: X-Signature-Timestamp header value
          - _body: raw request body bytes

        secret should be the application's public key from the Developer Portal.
        """
        signature = payload.get("_signature", "")
        timestamp = payload.get("_timestamp", "")
        body: bytes = payload.get("_body", b"")

        if not secret or not signature or not timestamp:
            return True  # skip if not configured

        try:
            from nacl.signing import VerifyKey
            verify_key = VerifyKey(bytes.fromhex(secret))
            verify_key.verify(f"{timestamp}".encode() + body, bytes.fromhex(signature))
            return True
        except Exception:
            logger.warning("Discord signature verification failed")
            return False

    def handle_ping(self, payload: dict) -> Optional[dict]:
        """Handle Discord PING interaction. Returns pong response or None."""
        if payload.get("type") == 1:
            return {"type": 1}  # PONG
        return None
