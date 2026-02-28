"""Symmetric encryption for storing user LLM API keys.

Uses Fernet (AES-128-CBC + HMAC-SHA256) derived from the platform SECRET_KEY.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from src.config import settings

logger = logging.getLogger(__name__)

# Salt for key derivation (stable, not secret — prevents rainbow table attacks)
_KEY_SALT = b"crewhub-fernet-v1"


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from the platform SECRET_KEY with salt."""
    digest = hashlib.sha256(_KEY_SALT + settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string and return the ciphertext as a URL-safe base64 string."""
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string. Returns empty string on failure.

    Logs a warning on decryption failure — this typically indicates a SECRET_KEY
    rotation without re-encrypting stored values.
    """
    try:
        f = Fernet(_derive_key())
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.warning(
            "Fernet decryption failed (InvalidToken). This may indicate SECRET_KEY "
            "was rotated without re-encrypting stored values. The encrypted value "
            "is now unreadable."
        )
        return ""
    except Exception:
        logger.warning("Fernet decryption failed with unexpected error.", exc_info=True)
        return ""
