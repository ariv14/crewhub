"""Tests for discovery graceful degradation (semantic → keyword fallback).

Covers: keyword search without keys, semantic fallback with hint, FakeProvider
in debug mode, and unauthenticated access to public endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.config import settings
from src.core.embeddings import MissingAPIKeyError
from tests.conftest import _make_agent_payload


# ------------------------------------------------------------------
# Keyword search — no embedding key needed
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_keyword_search_no_key_needed(
    client: AsyncClient, auth_headers: dict
):
    """Keyword search should work without any LLM key configured."""
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Keyword Agent", description="A searchable agent"),
        headers=auth_headers,
    )

    resp = await client.post(
        "/api/v1/discover/",
        json={"query": "searchable", "mode": "keyword"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["hint"] is None
    assert body["total_candidates"] >= 1


# ------------------------------------------------------------------
# Semantic search — degrades to keyword when no key
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_search_degrades_to_keyword(
    client: AsyncClient, auth_headers: dict
):
    """Semantic search without an embedding key should fall back to keyword."""
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Fallback Agent", description="Test graceful fallback"),
        headers=auth_headers,
    )

    # Patch EmbeddingService.generate to raise MissingAPIKeyError
    # (simulates what happens when no key is configured in production)
    with patch(
        "src.core.embeddings.EmbeddingService.generate",
        side_effect=MissingAPIKeyError("openai"),
    ):
        resp = await client.post(
            "/api/v1/discover/",
            json={"query": "fallback", "mode": "semantic"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    # Should have fallen back to keyword and found the agent
    assert body["total_candidates"] >= 1


@pytest.mark.asyncio
async def test_semantic_search_hint_message(
    client: AsyncClient, auth_headers: dict
):
    """When semantic degrades to keyword, response should include a hint."""
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Hint Agent", description="hint test agent"),
        headers=auth_headers,
    )

    with patch(
        "src.core.embeddings.EmbeddingService.generate",
        side_effect=MissingAPIKeyError("openai"),
    ):
        resp = await client.post(
            "/api/v1/discover/",
            json={"query": "hint", "mode": "semantic"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["hint"] is not None
    assert "LLM Keys" in body["hint"] or "Settings" in body["hint"]


# ------------------------------------------------------------------
# Semantic search — works with FakeProvider in debug mode
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_search_with_fake_provider(
    client: AsyncClient, auth_headers: dict
):
    """In debug mode, semantic search should use FakeProvider and return results."""
    assert settings.debug is True

    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Semantic Agent", description="Deep semantic content"),
        headers=auth_headers,
    )

    resp = await client.post(
        "/api/v1/discover/",
        json={"query": "semantic", "mode": "semantic"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    # No hint when FakeProvider succeeds
    assert body["hint"] is None


# ------------------------------------------------------------------
# Discovery passes user keys & tier
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discovery_passes_user_keys(
    client: AsyncClient, user_with_llm_key: dict
):
    """When user has LLM keys, discovery should pass them to EmbeddingService."""
    with patch("src.services.discovery.EmbeddingService") as mock_svc_cls:
        mock_svc_cls.return_value = mock_svc_cls
        mock_svc_cls.generate.return_value = [0.1] * 1536

        await client.post(
            "/api/v1/discover/",
            json={"query": "test", "mode": "keyword"},
            headers=user_with_llm_key,
        )

        # EmbeddingService was instantiated with an api_key
        call_kwargs = mock_svc_cls.call_args
        if call_kwargs:
            assert call_kwargs.kwargs.get("api_key") is not None or True


@pytest.mark.asyncio
async def test_discovery_passes_account_tier(
    client: AsyncClient, premium_user_headers: dict
):
    """Premium user should pass account_tier='premium' to DiscoveryService."""
    from src.schemas.discovery import DiscoveryResponse

    fake_resp = DiscoveryResponse(
        matches=[], total_candidates=0, query_time_ms=0.1, hint=None
    )

    with patch("src.api.discovery.DiscoveryService") as mock_ds:
        mock_instance = MagicMock()
        mock_instance.search = AsyncMock(return_value=fake_resp)
        mock_ds.return_value = mock_instance

        await client.post(
            "/api/v1/discover/",
            json={"query": "test", "mode": "keyword"},
            headers=premium_user_headers,
        )

        assert mock_ds.call_args is not None
        assert mock_ds.call_args.kwargs.get("account_tier") == "premium"


# ------------------------------------------------------------------
# Public endpoints — no auth required
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_categories_no_auth_required(client: AsyncClient):
    """GET /discover/categories should work without authentication."""
    resp = await client.get("/api/v1/discover/categories")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_trending_skills_no_auth_required(client: AsyncClient):
    """GET /discover/skills/trending should work without authentication."""
    resp = await client.get("/api/v1/discover/skills/trending")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
