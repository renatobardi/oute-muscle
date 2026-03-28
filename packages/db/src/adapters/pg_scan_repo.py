"""PostgreSQL adapter for Scan and Finding read/write operations.

Used by workers (rag_worker, synthesis_worker) that run outside the FastAPI
request lifecycle — no Depends() available, sessions are created directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.src.domain.incidents.enums import IncidentSeverity
from packages.db.src.models.finding import Finding as FindingModel
from packages.db.src.models.scan import Scan as ScanModel


class PostgreSQLScanRepo:
    """Read/write adapter for Scan rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        scan_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> ScanModel | None:
        """Load a Scan by primary key.

        Args:
            scan_id: The scan UUID.
            tenant_id: Optional tenant filter (skipped if None).

        Returns:
            ScanModel or None if not found.
        """
        stmt = select(ScanModel).where(ScanModel.id == scan_id)
        if tenant_id is not None:
            stmt = stmt.where(ScanModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_findings(self, scan_id: uuid.UUID) -> list[FindingModel]:
        """Return all Finding rows for the given scan.

        Args:
            scan_id: The scan UUID.

        Returns:
            List of FindingModel instances.
        """
        stmt = select(FindingModel).where(FindingModel.scan_id == scan_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        scan_id: uuid.UUID,
        *,
        status: str,
        completed_at: datetime | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Update the status (and optionally completed_at / duration_ms) of a scan.

        Args:
            scan_id: The scan to update.
            status: New status string ('completed', 'failed', 'timeout').
            completed_at: Timestamp when processing finished.
            duration_ms: Total processing time in milliseconds.
        """
        values: dict = {"status": status}
        if completed_at is not None:
            values["completed_at"] = completed_at
        if duration_ms is not None:
            values["duration_ms"] = duration_ms

        stmt = (
            update(ScanModel)
            .where(ScanModel.id == scan_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.commit()


def finding_severities(findings: list[FindingModel]) -> list[IncidentSeverity]:
    """Convert DB Finding rows to domain IncidentSeverity values for risk scoring.

    Unknown severity strings default to LOW.

    Args:
        findings: List of Finding SQLAlchemy models.

    Returns:
        List of IncidentSeverity enum values.
    """
    severity_map = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "medium": IncidentSeverity.MEDIUM,
        "low": IncidentSeverity.LOW,
    }
    result = []
    for f in findings:
        sev = severity_map.get(str(f.severity).lower(), IncidentSeverity.LOW)
        result.append(sev)
    return result
