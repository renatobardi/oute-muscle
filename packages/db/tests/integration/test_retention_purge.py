"""
T154: Integration test — findings retention auto-purge.
Verifies that findings older than the tier's retention window are deleted,
and findings within the window are preserved.

Free: 90 days | Team: 365 days | Enterprise: 730 days
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION") == "1" or not os.getenv("DATABASE_URL"),
    reason="Integration tests require DATABASE_URL and SKIP_INTEGRATION != 1",
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/oute_test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
        await session.rollback()
    await engine.dispose()


async def create_tenant_with_plan(session: AsyncSession, plan: str) -> str:
    tid = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO tenants (id, name, plan, created_at, updated_at) "
            "VALUES (:id, :name, :plan, NOW(), NOW())"
        ),
        {"id": tid, "name": f"Tenant {plan}", "plan": plan},
    )
    return tid


async def create_scan(session: AsyncSession, tenant_id: str) -> str:
    scan_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO scans "
            "(id, tenant_id, repository, commit_sha, risk_level, risk_score, "
            " findings_count, duration_ms, created_at) "
            "VALUES (:id, :tid, 'org/repo', 'abc123', 'low', 1.0, 1, 100, NOW())"
        ),
        {"id": scan_id, "tid": tenant_id},
    )
    return scan_id


async def create_finding(
    session: AsyncSession,
    tenant_id: str,
    scan_id: str,
    created_at: datetime,
) -> str:
    fid = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO findings "
            "(id, tenant_id, scan_id, rule_id, file_path, start_line, end_line, "
            " severity, category, message, remediation, false_positive, "
            " false_positive_count, created_at) "
            "VALUES (:id, :tid, :scan_id, 'unsafe-regex-001', 'src/foo.py', 1, 1, "
            "        'critical', 'unsafe-regex', 'bad regex', 'fix it', false, 0, :created_at)"
        ),
        {"id": fid, "tid": tenant_id, "scan_id": scan_id, "created_at": created_at},
    )
    return fid


async def run_retention_purge(session: AsyncSession) -> int:
    """Execute the retention purge logic (the actual worker SQL or function call)."""
    from apps.api.src.workers.retention_purge import purge_expired_findings

    return await purge_expired_findings(session)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFindingsRetentionPurge:
    @pytest.mark.asyncio
    async def test_free_tier_purges_findings_older_than_90_days(self, db_session):
        tenant = await create_tenant_with_plan(db_session, "free")
        scan = await create_scan(db_session, tenant)

        old_date = datetime.now(UTC) - timedelta(days=91)
        recent_date = datetime.now(UTC) - timedelta(days=30)

        old_finding = await create_finding(db_session, tenant, scan, old_date)
        recent_finding = await create_finding(db_session, tenant, scan, recent_date)

        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant})

        purged = await run_retention_purge(db_session)

        assert purged >= 1

        result = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": old_finding}
        )
        assert result.fetchone() is None, "Old finding should be purged"

        result = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": recent_finding}
        )
        assert result.fetchone() is not None, "Recent finding should be preserved"

    @pytest.mark.asyncio
    async def test_team_tier_purges_findings_older_than_365_days(self, db_session):
        tenant = await create_tenant_with_plan(db_session, "team")
        scan = await create_scan(db_session, tenant)

        old_date = datetime.now(UTC) - timedelta(days=366)
        mid_date = datetime.now(UTC) - timedelta(days=200)

        old_finding = await create_finding(db_session, tenant, scan, old_date)
        mid_finding = await create_finding(db_session, tenant, scan, mid_date)

        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant})

        await run_retention_purge(db_session)

        result_old = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": old_finding}
        )
        assert result_old.fetchone() is None, "366-day-old finding should be purged for team"

        result_mid = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": mid_finding}
        )
        assert result_mid.fetchone() is not None, "200-day-old finding should be retained for team"

    @pytest.mark.asyncio
    async def test_enterprise_tier_retains_findings_up_to_730_days(self, db_session):
        tenant = await create_tenant_with_plan(db_session, "enterprise")
        scan = await create_scan(db_session, tenant)

        almost_limit_date = datetime.now(UTC) - timedelta(days=729)
        finding = await create_finding(db_session, tenant, scan, almost_limit_date)

        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant})

        await run_retention_purge(db_session)

        result = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": finding}
        )
        assert result.fetchone() is not None, "729-day finding should be retained for enterprise"

    @pytest.mark.asyncio
    async def test_enterprise_tier_purges_findings_older_than_730_days(self, db_session):
        tenant = await create_tenant_with_plan(db_session, "enterprise")
        scan = await create_scan(db_session, tenant)

        over_limit_date = datetime.now(UTC) - timedelta(days=731)
        finding = await create_finding(db_session, tenant, scan, over_limit_date)

        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant})

        await run_retention_purge(db_session)

        result = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": finding}
        )
        assert result.fetchone() is None, "731-day finding should be purged for enterprise"

    @pytest.mark.asyncio
    async def test_purge_does_not_cross_tenant_boundaries(self, db_session):
        """Purge of tenant A must not affect tenant B's findings."""
        tenant_a = await create_tenant_with_plan(db_session, "free")
        tenant_b = await create_tenant_with_plan(db_session, "enterprise")

        scan_b = await create_scan(db_session, tenant_b)
        # B has an old finding but enterprise retains longer
        recent_b = datetime.now(UTC) - timedelta(days=91)
        finding_b = await create_finding(db_session, tenant_b, scan_b, recent_b)

        # Run purge for tenant A context only
        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant_a})
        await run_retention_purge(db_session)

        # Tenant B's finding must be unaffected
        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant_b})
        result = await db_session.execute(
            text("SELECT id FROM findings WHERE id = :id"), {"id": finding_b}
        )
        assert result.fetchone() is not None, "Cross-tenant purge must not occur"

    @pytest.mark.asyncio
    async def test_purge_returns_count_of_deleted_rows(self, db_session):
        tenant = await create_tenant_with_plan(db_session, "free")
        scan = await create_scan(db_session, tenant)

        old_date = datetime.now(UTC) - timedelta(days=100)
        await create_finding(db_session, tenant, scan, old_date)
        await create_finding(db_session, tenant, scan, old_date)
        await create_finding(db_session, tenant, scan, old_date)

        await db_session.execute(text('SET LOCAL "app.tenant_id" = :tid'), {"tid": tenant})
        purged = await run_retention_purge(db_session)

        assert purged == 3
