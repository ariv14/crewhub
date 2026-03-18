"""Slack adapter using Events API (webhook mode)."""
import hashlib
import hmac
import time
import logging
from typing import Optional

import httpx

from adapters.base import BasePlatformAdapter, NormalizedMessage

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


class SlackAdapter(BasePlatformAdapter):
    """Slack Events API adapter — webhook-based."""

    def parse_inbound(self, payload: dict) -> Optional[NormalizedMessage]:
        """Parse Slack Events API payload."""
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return None  # handled separately in webhook route

        event = payload.get("event", {})
        event_type = event.get("type")

        # Only handle messages (not bot messages, not edits)
        if event_type != "message" or event.get("subtype") or event.get("bot_id"):
            return None

        text = event.get("text", "")
        if not text:
            return None

        return NormalizedMessage(
            platform_user_id=event.get("user", ""),
            platform_message_id=event.get("client_msg_id", event.get("ts", "")),
            chat_id=event.get("channel", ""),
            text=text,
        )

    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool:
        """Send message via Slack chat.postMessage API."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{SLACK_API}/chat.postMessage",
                json={"channel": chat_id, "text": text},
                headers={"Authorization": f"Bearer {bot_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    return True
                logger.error("Slack postMessage error: %s", data.get("error"))
            else:
                logger.error("Slack postMessage HTTP %s", resp.status_code)
            return False

    async def send_typing(self, bot_token: str, chat_id: str) -> None:
        """Slack doesn't have a typing indicator API for bots."""
        pass

    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """Slack webhooks are configured in the Slack App dashboard, not via API.
        This is a no-op — the developer pastes the URL manually."""
        logger.info("Slack webhook must be configured manually in Slack App settings: %s", webhook_url)
        return True

    async def deregister_webhook(self, bot_token: str) -> bool:
        """No-op for Slack — developer removes in dashboard."""
        return True

    def verify_webhook(self, payload: dict, secret: Optional[str] = None) -> bool:
        """Verify Slack webhook signature using signing secret.

        Slack sends:
        - X-Slack-Request-Timestamp header
        - X-Slack-Signature header (v0=HMAC-SHA256)

        The payload must contain '_slack_timestamp' and '_slack_signature'
        keys injected by the webhook route before calling this method.
        """
        if not secret:
            return True  # skip verification if no secret configured

        timestamp = payload.get("_slack_timestamp", "")
        signature = payload.get("_slack_signature", "")
        raw_body = payload.get("_raw_body", "")

        if not timestamp or not signature:
            return True  # skip if headers not provided

        # Check timestamp freshness (within 5 minutes)
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 300:
                return False
        except ValueError:
            return False

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{raw_body}"
        expected = "v0=" + hmac.new(
            secret.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def handle_url_verification(self, payload: dict) -> Optional[str]:
        """Handle Slack URL verification challenge. Returns challenge string or None."""
        if payload.get("type") == "url_verification":
            return payload.get("challenge", "")
        return None
