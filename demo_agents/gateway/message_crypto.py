"""Encrypt/decrypt outbound message text (Fernet, versioned key)."""
import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

CURRENT_VERSION = "v1"

def _get_fernet(key: str) -> Fernet:
    derived = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))

def _get_keys() -> list[str]:
    keys = []
    primary = os.environ.get("CHANNEL_MESSAGE_KEY", "")
    if not primary:
        from config import settings
        primary = settings.gateway_service_key
        if primary:
            logger.warning("CHANNEL_MESSAGE_KEY not set — falling back to GATEWAY_SERVICE_KEY")
    if primary:
        keys.append(primary)
    old_key = os.environ.get("CHANNEL_MESSAGE_KEY_OLD", "")
    if old_key:
        keys.append(old_key)
    return keys

def encrypt_message(text: str) -> str:
    keys = _get_keys()
    if not keys:
        logger.error("No encryption key available — storing plaintext")
        return text
    return f"{CURRENT_VERSION}:{_get_fernet(keys[0]).encrypt(text.encode()).decode()}"

def decrypt_message(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    if not ciphertext.startswith(("v1:", "v2:")):
        return ciphertext  # legacy unencrypted
    _version, token = ciphertext.split(":", 1)
    for key in _get_keys():
        try:
            return _get_fernet(key).decrypt(token.encode()).decode()
        except InvalidToken:
            continue
    logger.error("Failed to decrypt message — no valid key found")
    return "[Decryption failed]"
