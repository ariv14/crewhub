"""Multi-provider embedding service with tiered rate limiting.

Supports: OpenAI, Google Gemini, Anthropic (via Voyager), Cohere, Ollama.

Tiered model:
  - Free tier: user provides any API key, rate limited to 50 requests/day
  - Premium tier: user provides any API key, no rate limit
  - Ollama: always allowed (local, no API key needed)
  - Debug mode: FakeProvider when no key is configured
"""

import hashlib
import logging
import struct
import time
from abc import ABC, abstractmethod

import httpx

from src.config import settings
from src.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MissingAPIKeyError — raised when no user key is configured
# ---------------------------------------------------------------------------


class MissingAPIKeyError(Exception):
    """Raised when an embedding provider requires an API key but none is configured."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(
            f"No API key configured for '{provider}'. "
            "Please add your key via Settings > LLM Keys."
        )


# ---------------------------------------------------------------------------
# Free-tier daily rate limiter (50 requests/day per user)
# ---------------------------------------------------------------------------

_FREE_TIER_MAX_PER_DAY = 50
# NOTE: In-memory counter works for single-process deployments.
# For multi-instance (Cloud Run, k8s), replace with Redis INCR + EXPIRE.
_free_tier_usage: dict[str, list[float]] = {}


def _check_free_tier_rate_limit(user_id: str, count: int = 1) -> None:
    """Rate-limit free-tier users to 50 embedding requests per day.

    Args:
        user_id: User identifier for rate tracking.
        count: Number of requests to consume (e.g., batch size).
    """
    now = time.time()
    day_ago = now - 86400

    if user_id not in _free_tier_usage:
        _free_tier_usage[user_id] = []

    _free_tier_usage[user_id] = [t for t in _free_tier_usage[user_id] if t > day_ago]

    if len(_free_tier_usage[user_id]) + count > _FREE_TIER_MAX_PER_DAY:
        raise RateLimitError(
            f"Free tier embedding limit reached ({_FREE_TIER_MAX_PER_DAY}/day). "
            "Upgrade to premium for unlimited usage, or wait until tomorrow."
        )

    _free_tier_usage[user_id].extend([now] * count)


# ---------------------------------------------------------------------------
# Provider base class
# ---------------------------------------------------------------------------


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        ...


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class OpenAIProvider(EmbeddingProvider):
    URL = "https://api.openai.com/v1/embeddings"
    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": texts, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------


class GeminiProvider(EmbeddingProvider):
    DEFAULT_MODEL = "gemini-embedding-001"

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:batchEmbedContents"
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = settings.embedding_dimension
        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]},
                "outputDimensionality": dim,
            }
            for t in texts
        ]
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.url,
                params={"key": self.api_key},
                json={"requests": requests},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["values"] for item in data["embeddings"]]


# ---------------------------------------------------------------------------
# Anthropic (Voyage AI — Anthropic's recommended embedding partner)
# ---------------------------------------------------------------------------


class AnthropicProvider(EmbeddingProvider):
    """Uses Voyage AI embeddings (voyage-3), recommended by Anthropic."""

    URL = "https://api.voyageai.com/v1/embeddings"
    DEFAULT_MODEL = "voyage-3"

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": texts, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]


# ---------------------------------------------------------------------------
# Cohere
# ---------------------------------------------------------------------------


class CohereProvider(EmbeddingProvider):
    URL = "https://api.cohere.com/v2/embed"
    DEFAULT_MODEL = "embed-english-v3.0"

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "texts": texts,
                    "model": self.model,
                    "input_type": "search_document",
                    "embedding_types": ["float"],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]["float"]


# ---------------------------------------------------------------------------
# Ollama (local, no API key needed)
# ---------------------------------------------------------------------------


class OllamaProvider(EmbeddingProvider):
    DEFAULT_MODEL = "nomic-embed-text"

    def __init__(self, base_url: str = "", model: str = ""):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.url = f"{self.base_url}/api/embed"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.url,
                json={"model": self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]


# ---------------------------------------------------------------------------
# Fake (deterministic, for dev/testing)
# ---------------------------------------------------------------------------


class FakeProvider(EmbeddingProvider):
    """Deterministic hash-based embeddings for dev/testing."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def _fake_embedding(self, text: str) -> list[float]:
        embedding: list[float] = []
        chunk_index = 0
        while len(embedding) < self.dimension:
            hash_input = f"{chunk_index}:{text}".encode("utf-8")
            digest = hashlib.sha512(hash_input).digest()
            values = struct.unpack(f"{len(digest) // 4}f", digest)
            for v in values:
                normalized = max(-1.0, min(1.0, v / 1e30))
                embedding.append(normalized)
                if len(embedding) >= self.dimension:
                    break
            chunk_index += 1
        return embedding[: self.dimension]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._fake_embedding(t) for t in texts]


# ---------------------------------------------------------------------------
# Factory + public service class
# ---------------------------------------------------------------------------

# Provider name → ProviderClass (all require user-supplied API key)
_PROVIDER_MAP: dict[str, type[EmbeddingProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
    "cohere": CohereProvider,
    "ollama": OllamaProvider,
}


def _build_provider(
    provider_name: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> EmbeddingProvider:
    """Build an embedding provider using the user's own API key.

    Resolution:
        1. Ollama: always allowed (local, no API key)
        2. Other providers: require user API key
        3. Debug mode: fall back to FakeProvider when no key is configured
        4. Production: raise MissingAPIKeyError
    """
    name = (provider_name or settings.embedding_provider).lower()
    mdl = model or settings.embedding_model

    if name == "ollama":
        return OllamaProvider(base_url=settings.ollama_base_url, model=mdl)

    if name in _PROVIDER_MAP:
        if api_key:
            return _PROVIDER_MAP[name](api_key=api_key, model=mdl)
        # No user key — try platform-owned key as fallback
        if settings.platform_embedding_key:
            logger.info("Using platform embedding key for '%s'", name)
            return _PROVIDER_MAP[name](api_key=settings.platform_embedding_key, model=mdl)
        # No platform key either — debug gets FakeProvider, production gets error
        if settings.debug:
            logger.info("No API key for '%s' in debug mode — using FakeProvider", name)
            return FakeProvider(dimension=settings.embedding_dimension)
        raise MissingAPIKeyError(name)

    # Unknown provider — debug gets FakeProvider, production gets error
    if settings.debug:
        return FakeProvider(dimension=settings.embedding_dimension)
    raise MissingAPIKeyError(name)


class EmbeddingService:
    """Public embedding interface with tiered rate limiting.

    Tier behaviour:
        - Free tier: 50 embedding requests/day (all providers)
        - Premium tier: unlimited
        - Ollama: no rate limit (local)
    """

    def __init__(
        self,
        provider_name: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        account_tier: str = "free",
    ):
        self._provider = _build_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model,
        )
        self._user_id = user_id
        self._account_tier = account_tier
        self._is_local = isinstance(self._provider, (OllamaProvider, FakeProvider))

    @property
    def provider_name(self) -> str:
        return type(self._provider).__name__.replace("Provider", "").lower()

    def _check_rate_limit(self, count: int = 1) -> None:
        """Enforce free-tier daily rate limit (skip for premium, local, or no user)."""
        if self._is_local or self._account_tier == "premium" or not self._user_id:
            return
        _check_free_tier_rate_limit(self._user_id, count)

    async def generate(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        self._check_rate_limit(1)
        results = await self._provider.embed([text])
        return results[0]

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        self._check_rate_limit(len(texts))
        return await self._provider.embed(texts)

    @classmethod
    def for_agent(
        cls,
        agent_embedding_config: dict | None = None,
        owner_llm_keys: dict | None = None,
    ) -> "EmbeddingService":
        """Create an EmbeddingService for agent registration (no rate limiting).

        Used during agent registration/update where the owner's keys are resolved
        but rate limiting is not applied (agent ops are admin-level).
        """
        provider_name = None
        model = None
        api_key = None

        if agent_embedding_config:
            provider_name = agent_embedding_config.get("provider")
            model = agent_embedding_config.get("model") or None

        resolved_provider = (provider_name or settings.embedding_provider).lower()
        if owner_llm_keys and resolved_provider in owner_llm_keys:
            api_key = owner_llm_keys[resolved_provider]

        return cls(
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            account_tier="premium",  # agent registration bypasses rate limits
        )
