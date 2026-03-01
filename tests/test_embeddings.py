"""Tests for the multi-provider embedding service (src/core/embeddings.py).

All tests use FakeProvider (debug mode) or direct instantiation — no external
API keys required.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.core.embeddings import (
    EmbeddingService,
    FakeProvider,
    MissingAPIKeyError,
    OpenAIProvider,
    _build_provider,
    _free_tier_usage,
)
from src.core.exceptions import RateLimitError
from src.config import settings


# Reusable mock for OpenAIProvider.embed — returns a fake embedding
_FAKE_EMBEDDING = [[0.1] * 1536]
_mock_embed = AsyncMock(return_value=_FAKE_EMBEDDING)


# ------------------------------------------------------------------
# FakeProvider behaviour
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fake_provider_deterministic():
    """FakeProvider should return the same embedding for the same text."""
    provider = FakeProvider(dimension=128)
    emb1 = (await provider.embed(["hello world"]))[0]
    emb2 = (await provider.embed(["hello world"]))[0]
    assert emb1 == emb2


@pytest.mark.asyncio
async def test_fake_provider_different_texts():
    """Different texts should produce different embeddings."""
    provider = FakeProvider(dimension=128)
    results = await provider.embed(["cat", "dog"])
    assert results[0] != results[1]


# ------------------------------------------------------------------
# MissingAPIKeyError
# ------------------------------------------------------------------


def test_missing_api_key_error_raised():
    """Provider=openai with no key and debug=False should raise MissingAPIKeyError."""
    original_debug = settings.debug
    try:
        settings.debug = False
        with pytest.raises(MissingAPIKeyError) as exc_info:
            _build_provider(provider_name="openai", api_key=None)
        assert "openai" in str(exc_info.value)
    finally:
        settings.debug = original_debug


def test_debug_mode_uses_fake_provider():
    """Provider=openai with no key and debug=True should return FakeProvider."""
    assert settings.debug is True  # Set in conftest
    provider = _build_provider(provider_name="openai", api_key=None)
    assert isinstance(provider, FakeProvider)


# ------------------------------------------------------------------
# Ollama provider resolution
# ------------------------------------------------------------------


def test_ollama_no_key_required():
    """Ollama provider should be created without an API key, even in non-debug."""
    original_debug = settings.debug
    try:
        settings.debug = False
        provider = _build_provider(provider_name="ollama", api_key=None)
        assert provider.__class__.__name__ == "OllamaProvider"
    finally:
        settings.debug = original_debug


# ------------------------------------------------------------------
# EmbeddingService init with key
# ------------------------------------------------------------------


def test_embedding_service_init_with_key():
    """Providing an API key should instantiate the correct provider."""
    svc = EmbeddingService(
        provider_name="openai",
        api_key="sk-real-key",
        user_id="u1",
        account_tier="free",
    )
    assert svc.provider_name == "openai"


# ------------------------------------------------------------------
# Free-tier rate limiting
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_free_tier_rate_limit_counter():
    """Free tier should allow 50 calls but reject the 51st."""
    svc = EmbeddingService(
        provider_name="openai",
        api_key="sk-test",
        user_id="rate-limit-user",
        account_tier="free",
    )

    with patch.object(svc._provider, "embed", new=AsyncMock(return_value=_FAKE_EMBEDDING)):
        for _ in range(50):
            await svc.generate("test text")

        with pytest.raises(RateLimitError):
            await svc.generate("one too many")


@pytest.mark.asyncio
async def test_premium_tier_bypasses_limit():
    """Premium tier should have no rate limit."""
    svc = EmbeddingService(
        provider_name="openai",
        api_key="sk-test",
        user_id="premium-user",
        account_tier="premium",
    )

    with patch.object(svc._provider, "embed", new=AsyncMock(return_value=_FAKE_EMBEDDING)):
        for _ in range(100):
            await svc.generate("test text")


@pytest.mark.asyncio
async def test_batch_generate_counts_each():
    """generate_batch should count each text toward the rate limit."""
    svc = EmbeddingService(
        provider_name="openai",
        api_key="sk-test",
        user_id="batch-user",
        account_tier="free",
    )

    with patch.object(
        svc._provider, "embed",
        new=AsyncMock(return_value=[[0.1] * 1536] * 48),
    ):
        await svc.generate_batch(["text"] * 48)

    with pytest.raises(RateLimitError):
        await svc.generate_batch(["text"] * 3)


# ------------------------------------------------------------------
# for_agent bypasses rate limit
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_for_agent_bypasses_rate_limit():
    """EmbeddingService.for_agent() should use premium tier (no rate limit)."""
    svc = EmbeddingService.for_agent()
    assert svc._account_tier == "premium"

    # Should handle many calls without rate limit error
    for _ in range(100):
        await svc.generate("agent embedding")
