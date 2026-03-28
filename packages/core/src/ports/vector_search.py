"""VectorSearch port — abstracts pgvector cosine similarity search."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..domain.incidents.entity import Incident


@dataclass(frozen=True)
class VectorSearchResult:
    """A single result from vector similarity search."""

    incident: Incident
    similarity_score: float  # cosine similarity 0.0-1.0 (higher = more similar)
    distance: float  # cosine distance 0.0-2.0 (lower = more similar)


@runtime_checkable
class VectorSearchPort(Protocol):
    """Port for vector similarity search over incident embeddings.

    Constitution IV: pgvector with HNSW indexes, partitioned by tenant.
    """

    async def find_similar(
        self,
        query_embedding: list[float],
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[VectorSearchResult]:
        """Find incidents most similar to the query embedding.

        Args:
            query_embedding: 768-dimensional query vector.
            tenant_id: If provided, includes tenant-specific incidents;
                       always includes public (tenant_id IS NULL) incidents.
            limit: Maximum number of results to return.
            min_similarity: Minimum cosine similarity threshold (0.0-1.0).

        Returns:
            List of results ordered by similarity descending.

        Raises:
            VectorSearchError: If the search fails.
        """
        ...


class VectorSearchError(Exception):
    """Raised when vector similarity search fails."""
