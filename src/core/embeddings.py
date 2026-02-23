"""Embedding generation service using OpenAI API."""

import hashlib
import struct

import httpx

from src.config import settings


class EmbeddingService:
    """Service for generating text embeddings via the OpenAI API.

    When no API key is configured, produces deterministic fake embeddings
    (hash-based) suitable for development and testing.
    """

    OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
    EMBEDDING_DIMENSION = 1536

    def __init__(
        self,
        api_key: str = "",
        model: str = "text-embedding-3-small",
    ):
        """Initialize the embedding service.

        Args:
            api_key: OpenAI API key. If empty, falls back to settings then
                     to fake embeddings.
            model: The embedding model to use.
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model

    def _fake_embedding(self, text: str) -> list[float]:
        """Generate a deterministic fake embedding from text using hashing.

        Produces a 1536-dimensional vector by repeatedly hashing the input
        text with different salts.

        Args:
            text: Input text.

        Returns:
            A list of 1536 floats in the range [-1, 1].
        """
        embedding: list[float] = []
        chunk_index = 0
        while len(embedding) < self.EMBEDDING_DIMENSION:
            hash_input = f"{chunk_index}:{text}".encode("utf-8")
            digest = hashlib.sha512(hash_input).digest()
            # Unpack 64 bytes as 8 doubles (8 bytes each)
            values = struct.unpack(f"{len(digest) // 4}f", digest)
            for v in values:
                # Normalize to [-1, 1] range using a simple tanh-like clamp
                normalized = max(-1.0, min(1.0, v / 1e30))
                embedding.append(normalized)
                if len(embedding) >= self.EMBEDDING_DIMENSION:
                    break
            chunk_index += 1
        return embedding[: self.EMBEDDING_DIMENSION]

    async def generate(self, text: str) -> list[float]:
        """Generate an embedding for a single text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        if not self.api_key:
            return self._fake_embedding(text)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.OPENAI_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "model": self.model,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: A list of input texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        if not texts:
            return []

        if not self.api_key:
            return [self._fake_embedding(text) for text in texts]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.OPENAI_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": texts,
                    "model": self.model,
                },
            )
            response.raise_for_status()
            data = response.json()
            # Sort by index to ensure correct ordering
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]
