"""PostgreSQL adapter for Scan and Finding read/write operations.

Used by workers (rag_worker, synthesis_worker) that run outside the FastAPI
request lifecycle — no Depends() available, sessions are created directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select, update
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

    async def create(
        self,
        *,
        scan_id: uuid.UUID,
        tenant_id: uuid.UUID,
        trigger_source: str,
        repository: str,
        commit_sha: str,
        pr_number: int | None = None,
        diff_lines: int = 0,
    ) -> ScanModel:
        """Insert a new Scan row in 'running' state.

        Args:
            scan_id: Pre-generated UUID so the caller knows the ID before commit.
            tenant_id: Owning tenant UUID.
            trigger_source: One of 'rest_api', 'github_push', 'github_pr', 'mcp'.
            repository: org/repo string.
            commit_sha: Git commit hash (up to 40 chars).
            pr_number: Pull request number if applicable.
            diff_lines: Number of lines in the diff.

        Returns:
            The newly created ScanModel (not yet committed — caller commits).
        """
        scan = ScanModel(
            id=scan_id,
            tenant_id=tenant_id,
            trigger_source=trigger_source,
            repository=repository,
            commit_sha=commit_sha or "unknown",
            pr_number=pr_number,
            diff_lines=diff_lines,
            status="running",
        )
        self._session.add(scan)
        return scan

    async def save_findings(
        self,
        scan_id: uuid.UUID,
        tenant_id: uuid.UUID,
        findings: list[dict[str, Any]],
    ) -> None:
        """Bulk-insert Finding rows for a scan.

        Args:
            scan_id: Parent scan UUID.
            tenant_id: Owning tenant UUID (for RLS).
            findings: List of finding dicts from _run_l1_semgrep().
        """
        for f in findings:
            incident_id_str = f.get("incident_id") or ""
            try:
                incident_id: uuid.UUID | None = (
                    uuid.UUID(incident_id_str) if incident_id_str else None
                )
            except ValueError:
                incident_id = None

            row = FindingModel(
                id=uuid.uuid4(),
                scan_id=scan_id,
                tenant_id=tenant_id,
                rule_id=f.get("rule_id", "unknown"),
                incident_id=incident_id,
                file_path=f.get("file_path", "unknown"),
                start_line=int(f.get("start_line", 1)),
                end_line=int(f.get("end_line", 1)),
                severity=f.get("severity", "low"),
                message=f.get("message", ""),
                remediation=f.get("remediation", ""),
            )
            self._session.add(row)

    async def complete(
        self,
        scan_id: uuid.UUID,
        *,
        findings_count: int,
        risk_level: str,
        risk_score: int,
        duration_ms: int,
        completed_at: datetime,
    ) -> None:
        """Mark a scan as completed with final metrics.

        Args:
            scan_id: The scan to update.
            findings_count: Total Layer 1 findings.
            risk_level: Derived risk level string.
            risk_score: Numeric risk score 0-100.
            duration_ms: Total scan duration in milliseconds.
            completed_at: Completion timestamp.
        """
        risk_to_score = {"low": 10, "medium": 40, "high": 70, "critical": 90}
        numeric_score = risk_to_score.get(risk_level, risk_to_score.get(risk_level, 10))
        stmt = (
            update(ScanModel)
            .where(ScanModel.id == scan_id)
            .values(
                status="completed",
                layer1_findings_count=findings_count,
                risk_level=risk_level,
                risk_score=numeric_score,
                duration_ms=duration_ms,
                completed_at=completed_at,
            )
        )
        await self._session.execute(stmt)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        repository: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ScanModel], int]:
        """Paginated scan list for a tenant, newest first.

        Args:
            tenant_id: Tenant UUID to filter by.
            repository: Optional repository filter.
            status: Optional status filter.
            offset: Rows to skip (pagination).
            limit: Max rows to return.

        Returns:
            Tuple of (list of ScanModel, total count).
        """
        from sqlalchemy import func

        base = select(ScanModel).where(ScanModel.tenant_id == tenant_id)
        if repository:
            base = base.where(ScanModel.repository == repository)
        if status:
            base = base.where(ScanModel.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        rows_stmt = base.order_by(desc(ScanModel.created_at)).offset(offset).limit(limit)
        rows_result = await self._session.execute(rows_stmt)
        rows = list(rows_result.scalars().all())
        return rows, total

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

        stmt = update(ScanModel).where(ScanModel.id == scan_id).values(**values)
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
