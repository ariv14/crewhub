"""Microsoft Teams adapter using Bot Framework (webhook mode)."""
import logging
import time
from typing import Optional

import httpx

from adapters.base import BasePlatformAdapter, NormalizedMessage

logger = logging.getLogger(__name__)

BOTFRAMEWORK_API = "https://smba.trafficmanager.net"
LOGIN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"


class TeamsAdapter(BasePlatformAdapter):
    """Microsoft Teams Bot Framework adapter — webhook-based."""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires: float = 0

    def parse_inbound(self, payload: dict) -> Optional[NormalizedMessage]:
        """Parse Bot Framework activity payload."""
        activity_type = payload.get("type")
        if activity_type != "message":
            return None

        text = payload.get("text", "")
        if not text:
            return None

        # Remove bot mention from text (Teams includes @botname in message)
        entities = payload.get("entities", [])
        for entity in entities:
            if entity.get("type") == "mention":
                mentioned = entity.get("mentioned", {})
                mention_text = entity.get("text", "")
                if mentioned.get("role") == "bot" or mentioned.get("id") == payload.get("recipient", {}).get("id"):
                    text = text.replace(mention_text, "").strip()

        if not text:
            return None

        from_user = payload.get("from", {})
        conversation = payload.get("conversation", {})

        return NormalizedMessage(
            platform_user_id=from_user.get("id", ""),
            platform_message_id=payload.get("id", ""),
            chat_id=conversation.get("id", ""),
            text=text,
        )

    async def _get_access_token(self, app_id: str, app_password: str) -> str:
        """Get Bot Framework OAuth token for sending messages."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                LOGIN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": app_id,
                    "client_secret": app_password,
                    "scope": "https://api.botframework.com/.default",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data["access_token"]
                self._token_expires = time.time() + data.get("expires_in", 3600) - 60
                return self._access_token
            logger.error("Teams token fetch failed: %s", resp.status_code)
            return ""

    async def send_message(self, bot_token: str, chat_id: str, text: str,
                           service_url: str = "", **kwargs) -> bool:
        """Send message via Bot Framework.

        bot_token is stored as 'app_id:app_password' format.
        service_url should be extracted from the inbound activity and passed
        via kwargs or the service_url parameter.
        """
        # Parse credentials
        if ":" in bot_token:
            app_id, app_password = bot_token.split(":", 1)
        else:
            logger.error("Teams bot_token must be 'app_id:app_password' format")
            return False

        if not service_url:
            service_url = BOTFRAMEWORK_API

        token = await self._get_access_token(app_id, app_password)
        if not token:
            return False

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{service_url}/v3/conversations/{chat_id}/activities",
                json={"type": "message", "text": text},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code in (200, 201):
                return True
            logger.error("Teams sendMessage failed: %s %s", resp.status_code, resp.text[:200])
            return False

    async def send_typing(self, bot_token: str, chat_id: str) -> None:
        """Send typing indicator via Bot Framework."""
        if ":" not in bot_token:
            return

        app_id, app_password = bot_token.split(":", 1)

        token = await self._get_access_token(app_id, app_password)
        if not token:
            return

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{BOTFRAMEWORK_API}/v3/conversations/{chat_id}/activities",
                    json={"type": "typing"},
                    headers={"Authorization": f"Bearer {token}"},
                )
        except Exception:
            pass  # best effort

    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """Teams webhooks are configured in Azure Bot registration.
        Developer must set the messaging endpoint URL manually."""
        logger.info("Teams messaging endpoint must be configured in Azure: %s", webhook_url)
        return True

    async def deregister_webhook(self, bot_token: str) -> bool:
        """No-op — developer removes in Azure Portal."""
        return True

    def verify_webhook(self, payload: dict, secret: Optional[str] = None) -> bool:
        """Teams webhook verification.

        Bot Framework uses JWT Bearer tokens for authentication.
        Full validation requires fetching Microsoft's OpenID config.
        For v1, we rely on the connection_id UUID in the URL.
        """
        # v1: accept all — URL contains UUID
        # v2: validate JWT Bearer token from Bot Framework
        return True
