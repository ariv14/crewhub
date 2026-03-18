"""Abstract base class for platform adapters."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class NormalizedMessage:
    """Platform-agnostic message representation."""
    platform_user_id: str
    platform_message_id: str
    chat_id: str
    text: str
    media_type: Optional[str] = None
    media_url: Optional[str] = None


class BasePlatformAdapter(ABC):
    """Interface that all platform adapters must implement."""

    @abstractmethod
    def parse_inbound(self, payload: dict) -> Optional[NormalizedMessage]:
        """Parse platform webhook payload into a NormalizedMessage. Returns None if not a user message."""
        ...

    @abstractmethod
    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool:
        """Send a text message to a chat. Returns True on success."""
        ...

    @abstractmethod
    async def send_typing(self, bot_token: str, chat_id: str) -> None:
        """Send typing indicator to a chat."""
        ...

    @abstractmethod
    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """Register webhook URL with the platform. Returns True on success."""
        ...

    @abstractmethod
    async def deregister_webhook(self, bot_token: str) -> bool:
        """Remove webhook registration. Returns True on success."""
        ...

    @abstractmethod
    def verify_webhook(self, payload: dict, secret: Optional[str] = None) -> bool:
        """Verify webhook signature/authenticity. Returns True if valid."""
        ...
