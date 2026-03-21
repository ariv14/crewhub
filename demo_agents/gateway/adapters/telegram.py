import hmac
import logging
import httpx
from .base import AbstractPlatformAdapter, NormalizedMessage

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"

class TelegramAdapter(AbstractPlatformAdapter):
    def verify_webhook(self, request_body: bytes, headers: dict, expected_secret: str = "") -> bool:
        """Verify Telegram webhook using X-Telegram-Bot-Api-Secret-Token header.

        Telegram sends the secret_token (set at setWebhook time) as this header
        on every webhook call. We use hmac.compare_digest for timing-safe comparison.
        """
        if not expected_secret:
            logger.warning("Telegram webhook received with no expected_secret configured — accepting but INSECURE")
            return True
        header_secret = headers.get("x-telegram-bot-api-secret-token", "")
        return hmac.compare_digest(header_secret, expected_secret)

    def parse_inbound(self, body: dict) -> NormalizedMessage | None:
        """Parse a Telegram Update object into a NormalizedMessage."""
        message = body.get("message") or body.get("edited_message")
        if not message:
            return None

        text = message.get("text", "")
        if not text:
            # Skip non-text messages (photos, stickers, etc.)
            return None

        return NormalizedMessage(
            platform_user_id=str(message["from"]["id"]),
            platform_message_id=str(message["message_id"]),
            platform_chat_id=str(message["chat"]["id"]),
            text=text,
        )

    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool:
        url = TELEGRAM_API.format(token=bot_token) + "/sendMessage"
        # Telegram has 4096 char limit per message — split if needed
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                for chunk in chunks:
                    resp = await client.post(url, json={
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "Markdown",
                    })
                    if resp.status_code != 200:
                        # Retry without markdown if parsing fails
                        await client.post(url, json={
                            "chat_id": chat_id,
                            "text": chunk,
                        })
            return True
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
            return False

    async def send_typing(self, bot_token: str, chat_id: str) -> None:
        url = TELEGRAM_API.format(token=bot_token) + "/sendChatAction"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "action": "typing",
                })
        except Exception:
            pass  # best-effort
