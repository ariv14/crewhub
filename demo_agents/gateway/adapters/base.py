from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NormalizedMessage:
    platform_user_id: str
    platform_message_id: str
    platform_chat_id: str
    text: str
    media_type: str = "text"

class AbstractPlatformAdapter(ABC):
    @abstractmethod
    def verify_webhook(self, request_body: bytes, headers: dict) -> bool: ...

    @abstractmethod
    def parse_inbound(self, body: dict) -> NormalizedMessage | None: ...

    @abstractmethod
    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool: ...

    @abstractmethod
    async def send_typing(self, bot_token: str, chat_id: str) -> None: ...

    def ack_response(self) -> dict:
        return {"ok": True}
