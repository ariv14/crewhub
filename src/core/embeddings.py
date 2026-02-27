"""Multi-provider embedding service.

Supports: OpenAI, Google Gemini, Anthropic (via Voyager), Cohere, Ollama.
Falls back to deterministic fake embeddings when no API key is configured.
"""

import hashlib
import struct
from abc import ABC, abstractmethod

import httpx

from src.config import settings

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
    DEFAULT_MODEL = "text-embedding-004"

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:batchEmbedContents"
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        requests = [
            {"model": f"models/{self.model}", "content": {"parts": [{"text": t}]}}
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

# Provider name → (api_key_setting, ProviderClass)
_PROVIDER_MAP = {
    "openai": ("openai_api_key", OpenAIProvider),
    "gemini": ("gemini_api_key", GeminiProvider),
    "anthropic": ("anthropic_api_key", AnthropicProvider),
    "cohere": ("cohere_api_key", CohereProvider),
    "ollama": (None, OllamaProvider),
}


def _build_provider() -> EmbeddingProvider:
    """Resolve the configured embedding provider, falling back to fake."""
    name = settings.embedding_provider.lower()

    if name == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model,
        )

    if name in _PROVIDER_MAP:
        key_attr, cls = _PROVIDER_MAP[name]
        api_key = getattr(settings, key_attr, "") if key_attr else ""
        if api_key:
            return cls(api_key=api_key, model=settings.embedding_model)

    # No valid provider/key — use fake embeddings
    return FakeProvider(dimension=settings.embedding_dimension)


class EmbeddingService:
    """Public embedding interface used by registry and discovery services.

    Provider is resolved once from settings. Callers don't need to know
    which provider is active.
    """

    def __init__(self):
        self._provider = _build_provider()

    @property
    def provider_name(self) -> str:
        return type(self._provider).__name__.replace("Provider", "").lower()

    async def generate(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        results = await self._provider.embed([text])
        return results[0]

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        return await self._provider.embed(texts)
