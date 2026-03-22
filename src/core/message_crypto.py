"""Decrypt outbound message text for display. Backend-side only."""
import base64
import hashlib
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def decrypt_message(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    if not ciphertext.startswith(("v1:", "v2:")):
        return ciphertext
    _version, token = ciphertext.split(":", 1)
    from src.config import settings
    keys = [k for k in [
        os.environ.get("CHANNEL_MESSAGE_KEY", ""),
        settings.gateway_service_key,
        os.environ.get("CHANNEL_MESSAGE_KEY_OLD", ""),
    ] if k]
    for key in keys:
        try:
            derived = hashlib.sha256(key.encode()).digest()
            f = Fernet(base64.urlsafe_b64encode(derived))
            return f.decrypt(token.encode()).decode()
        except InvalidToken:
            continue
    logger.error("Failed to decrypt channel message")
    return "[Decryption failed]"
