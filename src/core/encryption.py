"""Symmetric encryption for storing user LLM API keys.

Uses Fernet (AES-128-CBC + HMAC-SHA256) derived from the platform SECRET_KEY.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.config import settings


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from the platform SECRET_KEY."""
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string and return the ciphertext as a URL-safe base64 string."""
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string. Returns empty string on failure."""
    try:
        f = Fernet(_derive_key())
        return f.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return ""
