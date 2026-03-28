"""PostgreSQL adapter for Advisory persistence.

Persists Advisory domain entities produced by the RAG pipeline into the
advisory table. Used by rag_worker and the scans route (inline L2).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.src.domain.scanning.entities import Advisory as AdvisoryEntity
from packages.db.src.models.advisory import Advisory as AdvisoryModel


class PostgreSQLAdvisoryRepo:
    """Write-only adapter for Advisory rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, advisory: AdvisoryEntity) -> None:
        """Persist an Advisory domain entity to the database.

        Field mapping (domain → DB column):
            id               → id
            scan_id          → scan_id
            tenant_id        → tenant_id
            incident_id      → incident_id
            confidence_score → confidence
            analysis_text    → reasoning
            matched_anti_pattern → remediation_notes

        Args:
            advisory: Advisory entity produced by RAGPipeline.
        """
        model = AdvisoryModel(
            id=advisory.id,
            scan_id=advisory.scan_id,
            tenant_id=advisory.tenant_id,
            incident_id=advisory.incident_id,
            confidence=advisory.confidence_score,
            reasoning=advisory.analysis_text,
            remediation_notes=advisory.matched_anti_pattern,
        )
        self._session.add(model)
        await self._session.commit()

    async def list_by_scan(self, scan_id: uuid.UUID) -> list[AdvisoryModel]:
        """Return all advisories for a given scan.

        Args:
            scan_id: The scan UUID.

        Returns:
            List of AdvisoryModel instances.
        """
        from sqlalchemy import select

        stmt = select(AdvisoryModel).where(AdvisoryModel.scan_id == scan_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
