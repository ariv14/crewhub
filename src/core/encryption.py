# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Symmetric encryption with key versioning for stored secrets.

Uses Fernet (AES-128-CBC + HMAC-SHA256). Supports key rotation via version
prefixes on ciphertext: 'v1:<token>'. Legacy bare tokens (no prefix) are
handled transparently for backward compatibility.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from src.config import settings

logger = logging.getLogger(__name__)

CURRENT_VERSION = "v1"

_VERSION_SALT = {
    "v1": b"crewhub-fernet-v1",
}


def _derive_key_for_version(version: str) -> bytes:
    """Derive a Fernet key for a specific version."""
    salt = _VERSION_SALT.get(version)
    if salt is None:
        raise ValueError(f"Unknown encryption key version: {version}")
    raw_key = settings.encryption_key or settings.secret_key
    digest = hashlib.sha256(salt + raw_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """Encrypt and return versioned ciphertext: 'v1:<fernet_token>'."""
    key = _derive_key_for_version(CURRENT_VERSION)
    token = Fernet(key).encrypt(plaintext.encode()).decode()
    return f"{CURRENT_VERSION}:{token}"


def decrypt_value(ciphertext: str) -> str:
    """Decrypt versioned ciphertext. Handles legacy unversioned values.

    Returns empty string on failure (logs a warning).
    """
    if ":" in ciphertext and ciphertext.split(":")[0] in _VERSION_SALT:
        version, token = ciphertext.split(":", 1)
    else:
        # Legacy value — no version prefix, use v1 key
        version, token = "v1", ciphertext

    try:
        key = _derive_key_for_version(version)
        return Fernet(key).decrypt(token.encode()).decode()
    except InvalidToken:
        logger.warning(
            "Fernet decryption failed (InvalidToken) for version %s. "
            "This may indicate a key rotation without re-encryption.",
            version,
        )
        return ""
    except Exception:
        logger.warning("Fernet decryption failed with unexpected error.", exc_info=True)
        return ""
