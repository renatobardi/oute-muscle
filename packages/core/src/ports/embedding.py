"""Embedding port — abstracts Vertex AI text-embedding-005.

Constitution IV: Embeddings via Vertex AI text-embedding-005, 768 dimensions.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


EMBEDDING_DIMENSIONS = 768  # text-embedding-005 output size


@runtime_checkable
class EmbeddingPort(Protocol):
    """Port for generating vector embeddings from text."""

    async def embed(self, text: str) -> list[float]:
        """Generate a 768-dimensional embedding for a single text.

        Args:
            text: Input text to embed.

        Returns:
            List of 768 floats representing the embedding vector.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of input texts to embed.

        Returns:
            List of 768-dimensional embedding vectors, one per input text.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        ...


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
