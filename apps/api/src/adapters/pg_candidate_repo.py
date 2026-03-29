"""PostgreSQL adapter for SynthesisCandidate query operations.

Implements the SynthesisCandidateQueryRepo Protocol defined in
apps/api/src/routes/synthesis.py.  Operations are read-heavy; writes
(create, update_status) are also supported for the approval workflow.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from packages.db.src.models.synthesis_candidate import SynthesisCandidate

logger = logging.getLogger(__name__)


class PostgreSQLCandidateRepo:
    """PostgreSQL-backed synthesis candidate repository.

    Uses SessionFactory rather than a per-request session because synthesis
    routes inject this via app.state (not via FastAPI Depends).
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def list_by_tenant(
        self,
        tenant_id: str,
        status_filter: Any | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Any], int]:
        """Return paginated candidates for a tenant.

        Args:
            tenant_id: Tenant UUID string.
            status_filter: CandidateStatus enum or None (no filter).
            page: 1-based page number.
            page_size: Max rows per page.

        Returns:
            Tuple of (list of SynthesisCandidate, total count).
        """
        from sqlalchemy import desc, func, select

        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            return [], 0

        async for session in self._session_factory.get_session():
            try:
                base = select(SynthesisCandidate).where(
                    SynthesisCandidate.tenant_id == tenant_uuid
                )
                if status_filter is not None:
                    base = base.where(SynthesisCandidate.status == str(status_filter))

                count_result = await session.execute(
                    select(func.count()).select_from(base.subquery())
                )
                total = count_result.scalar_one()

                rows_result = await session.execute(
                    base.order_by(desc(SynthesisCandidate.created_at))
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
                rows = list(rows_result.scalars().all())
                return rows, total
            except Exception as exc:
                logger.warning("list_by_tenant failed: %s", exc)
                return [], 0

        return [], 0

    async def get(self, candidate_id: str) -> Any | None:
        """Fetch a single candidate by ID.

        Args:
            candidate_id: UUID string of the candidate.

        Returns:
            SynthesisCandidate or None if not found.
        """
        from sqlalchemy import select

        try:
            cid = uuid.UUID(candidate_id)
        except ValueError:
            return None

        async for session in self._session_factory.get_session():
            try:
                result = await session.execute(
                    select(SynthesisCandidate).where(SynthesisCandidate.id == cid)
                )
                return result.scalar_one_or_none()
            except Exception as exc:
                logger.warning("get candidate %s failed: %s", candidate_id, exc)
                return None

        return None

    async def create(self, candidate: Any) -> Any:
        """Persist a new synthesis candidate.

        Args:
            candidate: SynthesisCandidate domain object or model.

        Returns:
            The persisted candidate.
        """
        async for session in self._session_factory.get_session():
            try:
                session.add(candidate)
                await session.commit()
                await session.refresh(candidate)
                return candidate
            except Exception as exc:
                await session.rollback()
                logger.error("create candidate failed: %s", exc)
                raise

        raise RuntimeError("No session available")

    async def update_status(
        self,
        candidate_id: str,
        status: Any,
        failure_reason: str | None = None,
        increment_failure_count: bool = False,
    ) -> None:
        """Update the status of a synthesis candidate.

        Args:
            candidate_id: UUID string of the candidate.
            status: New CandidateStatus value.
            failure_reason: Optional failure description.
            increment_failure_count: Whether to increment the failure counter.
        """
        from sqlalchemy import update

        try:
            cid = uuid.UUID(candidate_id)
        except ValueError:
            logger.warning("Invalid candidate_id: %s", candidate_id)
            return

        values: dict[str, Any] = {"status": str(status)}
        if failure_reason is not None:
            values["failure_reason"] = failure_reason

        async for session in self._session_factory.get_session():
            try:
                await session.execute(
                    update(SynthesisCandidate)
                    .where(SynthesisCandidate.id == cid)
                    .values(**values)
                )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error("update_status failed for %s: %s", candidate_id, exc)
            return

    async def list_stale_pending(self, older_than_days: int) -> list[Any]:
        """Return pending candidates older than the given number of days.

        Args:
            older_than_days: Age threshold in days.

        Returns:
            List of stale SynthesisCandidate rows.
        """
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import select

        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)

        async for session in self._session_factory.get_session():
            try:
                result = await session.execute(
                    select(SynthesisCandidate)
                    .where(SynthesisCandidate.status == "pending")
                    .where(SynthesisCandidate.created_at < cutoff)
                )
                return list(result.scalars().all())
            except Exception as exc:
                logger.warning("list_stale_pending failed: %s", exc)
                return []

        return []
