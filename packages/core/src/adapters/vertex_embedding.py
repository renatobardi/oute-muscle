"""Vertex AI embedding adapter (EmbeddingPort implementation).

Constitution VI: Adapter implements port with real Vertex AI API calls.
Uses text-embedding-005 model for 768-dimensional embeddings.
"""

from __future__ import annotations

from ..ports.embedding import EmbeddingPort


class VertexAIEmbedding(EmbeddingPort):
    """Vertex AI adapter for EmbeddingPort."""

    async def embed(self, text: str) -> list[float]:
        """Generate 768-dimensional embedding for text."""
        raise NotImplementedError("Vertex AI embedding adapter implementation pending")
