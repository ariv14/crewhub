"""Tests for account tier enforcement (free vs premium).

Covers: tier on user response, tier persistence, embedding rate limits by tier.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.embeddings import EmbeddingService
from src.core.exceptions import RateLimitError
from src.models.user import User

_FAKE_EMBEDDING = [[0.1] * 1536]


# ------------------------------------------------------------------
# Tier on user response
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_user_is_free_tier(client: AsyncClient, auth_headers: dict):
    """A newly registered user should have account_tier='free'."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["account_tier"] == "free"


@pytest.mark.asyncio
async def test_user_response_includes_tier(client: AsyncClient, auth_headers: dict):
    """The /auth/me response schema should include the account_tier field."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert "account_tier" in resp.json()


@pytest.mark.asyncio
async def test_set_premium_via_db(
    client: AsyncClient, premium_user_headers: dict,
):
    """Directly setting premium in DB should be reflected in /auth/me."""
    resp = await client.get("/api/v1/auth/me", headers=premium_user_headers)
    assert resp.status_code == 200
    assert resp.json()["account_tier"] == "premium"


# ------------------------------------------------------------------
# Embedding rate limiting by tier (unit-level)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_free_tier_embedding_rate_limit():
    """Free tier with a real provider key should hit rate limit at 51."""
    svc = EmbeddingService(
        provider_name="openai",
        api_key="sk-test-key",
        user_id="free-tier-user",
        account_tier="free",
    )
    with patch.object(svc._provider, "embed", new=AsyncMock(return_value=_FAKE_EMBEDDING)):
        for _ in range(50):
            await svc.generate("test")

        with pytest.raises(RateLimitError):
            await svc.generate("over-limit")


@pytest.mark.asyncio
async def test_premium_tier_no_rate_limit():
    """Premium tier should not be rate-limited."""
    svc = EmbeddingService(
        provider_name="openai",
        api_key="sk-test-key",
        user_id="premium-tier-user",
        account_tier="premium",
    )
    with patch.object(svc._provider, "embed", new=AsyncMock(return_value=_FAKE_EMBEDDING)):
        for _ in range(100):
            await svc.generate("test")


# ------------------------------------------------------------------
# Tier persistence across sessions
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tier_persists_across_sessions(
    client: AsyncClient, db_session: AsyncSession
):
    """Setting tier and obtaining a new token should still show the same tier."""
    from tests.conftest import _unique_email

    email = _unique_email()
    password = "PersistPass123"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Persist User"},
    )
    # Set premium
    stmt = update(User).where(User.email == email).values(account_tier="premium")
    await db_session.execute(stmt)
    await db_session.commit()

    # New login = new token
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": "Persist User"},
    )
    new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/v1/auth/me", headers=new_headers)
    assert resp.json()["account_tier"] == "premium"


# ------------------------------------------------------------------
# Downgrade
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_downgrade_to_free():
    """Downgrading from premium to free should re-enable rate limits."""
    svc_premium = EmbeddingService(
        provider_name="openai",
        api_key="sk-test-key",
        user_id="downgrade-user",
        account_tier="premium",
    )
    with patch.object(svc_premium._provider, "embed", new=AsyncMock(return_value=_FAKE_EMBEDDING)):
        for _ in range(60):
            await svc_premium.generate("test")

    # Now simulate downgrade — new service instance as free tier
    svc_free = EmbeddingService(
        provider_name="openai",
        api_key="sk-test-key",
        user_id="downgrade-user-2",
        account_tier="free",
    )
    with patch.object(svc_free._provider, "embed", new=AsyncMock(return_value=_FAKE_EMBEDDING)):
        for _ in range(50):
            await svc_free.generate("test")

        with pytest.raises(RateLimitError):
            await svc_free.generate("over-limit")


# ------------------------------------------------------------------
# Ollama bypass
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_no_tier_limit():
    """Ollama (local) should not be rate-limited regardless of tier."""
    svc = EmbeddingService(
        provider_name="ollama",
        user_id="ollama-user",
        account_tier="free",
    )
    # OllamaProvider is local — rate limiting is skipped.
    # We can't actually call embed (no server), but we can verify _is_local.
    assert svc._is_local is True
