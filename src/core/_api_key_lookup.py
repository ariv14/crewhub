"""API key lookup — resolves an API key to a user via HMAC-SHA256 hash."""

import hashlib
import hmac

from sqlalchemy import select

from src.config import settings
from src.database import async_session
from src.models.user import User


def hash_api_key(api_key: str) -> str:
    """HMAC-SHA256 hash of an API key for storage and lookup."""
    return hmac.new(
        settings.secret_key.encode(), api_key.encode(), hashlib.sha256
    ).hexdigest()


async def lookup_user_by_api_key(api_key: str) -> dict | None:
    """Look up a user by their API key.

    Hashes the provided key with SHA-256 and matches against stored hashes.
    Returns dict with 'id' and 'email' if found, None otherwise.
    """
    key_hash = hash_api_key(api_key)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.api_key_hash == key_hash, User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()

        if user is None:
            return None

        if user.api_key_revoked_at is not None:
            return None

        return {"id": str(user.id), "email": user.email}
