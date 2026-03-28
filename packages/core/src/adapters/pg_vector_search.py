"""PostgreSQL pgvector search adapter (VectorSearchPort implementation).

Constitution VI: Adapter implements port with pgvector cosine similarity search.
Uses HNSW index for efficient similarity search on 768-dimensional embeddings.
"""

from __future__ import annotations

import uuid

from ..domain.incidents.entity import Incident
from ..ports.vector_search import VectorSearchPort


class PostgreSQLVectorSearch(VectorSearchPort):
    """PostgreSQL pgvector adapter for VectorSearchPort."""

    async def find_similar(
        self,
        embedding: list[float],
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[Incident]:
        """Find incidents similar to the given embedding (cosine distance)."""
        raise NotImplementedError("PostgreSQL vector search adapter implementation pending")
