"""WhatsApp adapter using Meta Cloud API."""
import hashlib
import hmac
import logging
import time
from typing import Optional

import httpx

from adapters.base import BasePlatformAdapter, NormalizedMessage

logger = logging.getLogger(__name__)

WHATSAPP_API = "https://graph.facebook.com/v21.0"

# Track conversation windows per (connection_id, user_phone)
# key: "conn_id:phone" → expiry timestamp
_conversation_windows: dict[str, float] = {}


class WhatsAppAdapter(BasePlatformAdapter):
    """Meta WhatsApp Cloud API adapter — webhook-based, premium channel."""

    CREDIT_SURCHARGE = 2  # extra credits per new conversation window

    def parse_inbound(self, payload: dict) -> Optional[NormalizedMessage]:
        """Parse WhatsApp Cloud API webhook payload."""
        entry = payload.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        msg_type = msg.get("type")

        # v1: text only
        if msg_type != "text":
            return None

        text = msg.get("text", {}).get("body", "")
        if not text:
            return None

        from_phone = msg.get("from", "")
        msg_id = msg.get("id", "")

        return NormalizedMessage(
            platform_user_id=from_phone,
            platform_message_id=msg_id,
            chat_id=from_phone,  # WhatsApp uses phone number as chat ID
            text=text,
        )

    def is_within_conversation_window(self, connection_id: str, user_phone: str) -> bool:
        """Check if we're within the 24h conversation window (no surcharge needed)."""
        key = f"{connection_id}:{user_phone}"
        expiry = _conversation_windows.get(key, 0)
        return time.time() < expiry

    def open_conversation_window(self, connection_id: str, user_phone: str):
        """Open/extend a 24h conversation window."""
        key = f"{connection_id}:{user_phone}"
        _conversation_windows[key] = time.time() + 86400  # 24 hours

    def get_surcharge(self, connection_id: str, user_phone: str) -> int:
        """Return credit surcharge: 2 if new window, 0 if within existing window."""
        if self.is_within_conversation_window(connection_id, user_phone):
            return 0
        return self.CREDIT_SURCHARGE

    async def send_message(self, bot_token: str, chat_id: str, text: str,
                           phone_number_id: str = "") -> bool:
        """Send message via WhatsApp Cloud API."""
        if not phone_number_id:
            logger.error("WhatsApp phone_number_id required")
            return False

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{WHATSAPP_API}/{phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": chat_id,
                    "type": "text",
                    "text": {"preview_url": False, "body": text[:4096]},
                },
                headers={"Authorization": f"Bearer {bot_token}"},
            )
            if resp.status_code == 200:
                return True
            logger.error("WhatsApp sendMessage failed: %s %s", resp.status_code, resp.text[:200])
            return False

    async def send_typing(self, bot_token: str, chat_id: str, phone_number_id: str = "") -> None:
        """Mark message as read (closest to typing indicator on WhatsApp)."""
        if not phone_number_id:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{WHATSAPP_API}/{phone_number_id}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "status": "read",
                        "message_id": "placeholder",  # would need actual message ID
                    },
                    headers={"Authorization": f"Bearer {bot_token}"},
                )
        except Exception:
            pass

    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """WhatsApp webhooks are configured in Meta App Dashboard.
        Developer must set the callback URL and verify token manually."""
        logger.info("WhatsApp webhook must be configured in Meta App Dashboard: %s", webhook_url)
        return True

    async def deregister_webhook(self, bot_token: str) -> bool:
        """No-op — developer removes in Meta Dashboard."""
        return True

    def verify_webhook(self, payload: dict, secret: Optional[str] = None,
                       signature: str = "", body: bytes = b"") -> bool:
        """Verify WhatsApp webhook signature.

        Meta sends X-Hub-Signature-256 header with HMAC-SHA256.
        """
        if not secret or not signature:
            return True  # skip if not configured

        expected = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def handle_verification_challenge(self, mode: str, token: str,
                                       challenge: str, verify_token: str) -> Optional[str]:
        """Handle Meta webhook verification GET request.

        Meta sends:
        - hub.mode = "subscribe"
        - hub.verify_token = your configured token
        - hub.challenge = challenge string to return
        """
        if mode == "subscribe" and token == verify_token:
            return challenge
        return None
