"""
T158: Findings retention scheduled job.

Purges findings older than the tenant's plan-specific retention window:
  Free:       90 days
  Team:      365 days
  Enterprise: 730 days

Designed to run as a Cloud Run Job (or Cloud Scheduler trigger).
Can also be invoked programmatically in tests.

Entry point: ``python -m apps.api.src.workers.retention_purge``
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from packages.core.src.domain.tenants.plan_limits import PlanLimits, Plan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core purge function (testable)
# ---------------------------------------------------------------------------

async def purge_expired_findings(session: AsyncSession) -> int:
    """
    Delete findings that exceed the retention window for their tenant's plan.
    Operates only on the tenant set in ``app.tenant_id`` (respects RLS).

    Returns the number of deleted rows.
    """
    # Build per-plan cutoff expressions and run one DELETE per plan tier
    total_deleted = 0

    for plan in (Plan.FREE, Plan.TEAM, Plan.ENTERPRISE):
        retention_days = PlanLimits.retention_days(plan)
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        result = await session.execute(
            text(
                """
                DELETE FROM findings
                WHERE created_at < :cutoff
                  AND tenant_id IN (
                      SELECT id FROM tenants WHERE plan = :plan
                  )
                RETURNING id
                """
            ),
            {"cutoff": cutoff, "plan": plan.value},
        )
        deleted = len(result.fetchall())
        total_deleted += deleted

        if deleted:
            logger.info(
                "retention_purge plan=%s cutoff=%s deleted=%d",
                plan.value,
                cutoff.isoformat(),
                deleted,
            )

    return total_deleted


# ---------------------------------------------------------------------------
# Standalone runner (Cloud Run Job entry point)
# ---------------------------------------------------------------------------

async def _run() -> None:
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total = 0

    async with async_session() as session:
        async with session.begin():
            total = await purge_expired_findings(session)

    await engine.dispose()
    logger.info("retention_purge complete total_deleted=%d", total)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())
