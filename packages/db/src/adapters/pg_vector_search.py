"""PostgreSQL pgvector search adapter — real implementation of VectorSearchPort.

Constitution VI: Adapter implements port with pgvector cosine similarity search.
Uses HNSW index for efficient similarity search on 768-dimensional embeddings.

Placed in packages/db because it needs SQLAlchemy + pgvector deps.
"""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.src.domain.incidents.entity import Incident as IncidentEntity
from packages.core.src.domain.incidents.enums import IncidentCategory, IncidentSeverity

from ..models.incident import Incident as IncidentModel


def _model_to_entity(model: IncidentModel) -> IncidentEntity:
    """Convert SQLAlchemy Incident model to domain entity."""
    return IncidentEntity(
        id=model.id,
        tenant_id=model.tenant_id,
        title=model.title,
        date=model.date,
        source_url=model.source_url,
        organization=model.organization,
        category=IncidentCategory(model.category),
        subcategory=model.subcategory,
        failure_mode=model.failure_mode,
        severity=IncidentSeverity(model.severity),
        affected_languages=list(model.affected_languages) if model.affected_languages else [],
        anti_pattern=model.anti_pattern,
        code_example=model.code_example,
        remediation=model.remediation,
        tags=list(model.tags) if model.tags else [],
        static_rule_possible=bool(model.static_rule_possible),
        semgrep_rule_id=model.semgrep_rule_id,
        embedding=list(model.embedding) if model.embedding is not None else None,
        version=model.version,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=model.created_by or uuid.UUID(int=0),
    )


class PostgreSQLVectorSearch:
    """PostgreSQL pgvector adapter for VectorSearchPort.

    Uses cosine distance on the HNSW index for sub-second similarity search.
    Filters by tenant_id (and shared incidents with tenant_id IS NULL).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_similar(
        self,
        embedding: list[float],
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[IncidentEntity]:
        """Find incidents most similar to the given embedding vector.

        Uses pgvector cosine distance operator (<=>).
        Excludes soft-deleted incidents and those without embeddings.

        Args:
            embedding: 768-dimensional query embedding.
            tenant_id: If provided, restricts to tenant + shared (NULL) incidents.
            limit: Maximum number of results to return.

        Returns:
            List of incidents ordered by cosine similarity (most similar first).
        """
        stmt = (
            select(IncidentModel)
            .where(
                IncidentModel.deleted_at.is_(None),
                IncidentModel.embedding.is_not(None),
            )
            .order_by(IncidentModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )

        if tenant_id is not None:
            stmt = stmt.where(
                or_(
                    IncidentModel.tenant_id == tenant_id,
                    IncidentModel.tenant_id.is_(None),
                )
            )

        result = await self._session.execute(stmt)
        return [_model_to_entity(m) for m in result.scalars().all()]
