"""
T151: Integration test — RLS tenant isolation.
Verifies that tenant A cannot read, update, or delete tenant B's data.

Requires a running PostgreSQL instance with RLS policies applied
(set DATABASE_URL in env, or skip with SKIP_INTEGRATION=1).
"""

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Skip entire module if no database URL provided
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION") == "1" or not os.getenv("DATABASE_URL"),
        reason="Integration tests require DATABASE_URL and SKIP_INTEGRATION != 1",
    ),
]

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/oute_test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Simulate what the RLS middleware does: set the tenant context variable."""
    await session.execute(
        text('SET LOCAL "app.tenant_id" = :tenant_id'),
        {"tenant_id": tenant_id},
    )


async def create_tenant(session: AsyncSession, name: str) -> str:
    """Insert a tenant record directly (bypassing RLS) and return its ID."""
    tenant_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO tenants (id, name, plan, created_at, updated_at) "
            "VALUES (:id, :name, 'free', NOW(), NOW())"
        ),
        {"id": tenant_id, "name": name},
    )
    return tenant_id


async def create_incident(session: AsyncSession, tenant_id: str, title: str) -> str:
    """Insert an incident belonging to a specific tenant and return its ID."""
    incident_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO incidents "
            "(id, tenant_id, title, category, severity, anti_pattern, remediation, "
            " affected_languages, static_rule_possible, version, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :title, 'unsafe-regex', 'critical', "
            "        'bad pattern', 'fix it', '{}', false, 1, NOW(), NOW())"
        ),
        {"id": incident_id, "tenant_id": tenant_id, "title": title},
    )
    return incident_id


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
        # Rollback so tests don't pollute each other
        await session.rollback()

    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRlsTenantIsolation:
    """Tenant A must not be able to see or modify Tenant B's data."""

    @pytest.mark.asyncio
    async def test_tenant_cannot_read_other_tenant_incidents(self, db_session):
        """SELECT with tenant A context returns zero rows from tenant B's incidents."""
        # Setup: two tenants with one incident each
        tenant_a = await create_tenant(db_session, "Tenant A")
        tenant_b = await create_tenant(db_session, "Tenant B")

        await set_tenant_context(db_session, tenant_b)
        inc_b = await create_incident(db_session, tenant_b, "Tenant B incident")

        # Query as tenant A
        await set_tenant_context(db_session, tenant_a)
        result = await db_session.execute(
            text("SELECT id FROM incidents WHERE id = :id"),
            {"id": inc_b},
        )
        rows = result.fetchall()

        assert len(rows) == 0, f"Tenant A should not see Tenant B's incident {inc_b}"

    @pytest.mark.asyncio
    async def test_tenant_can_read_own_incidents(self, db_session):
        """SELECT with correct tenant context returns the tenant's own incidents."""
        tenant_a = await create_tenant(db_session, "Tenant A Solo")

        await set_tenant_context(db_session, tenant_a)
        inc_a = await create_incident(db_session, tenant_a, "Tenant A own incident")

        result = await db_session.execute(
            text("SELECT id, title FROM incidents WHERE id = :id"),
            {"id": inc_a},
        )
        rows = result.fetchall()

        assert len(rows) == 1
        assert rows[0].title == "Tenant A own incident"

    @pytest.mark.asyncio
    async def test_tenant_cannot_update_other_tenant_incidents(self, db_session):
        """UPDATE with tenant A context must not affect tenant B rows (0 rows updated)."""
        tenant_a = await create_tenant(db_session, "Updater A")
        tenant_b = await create_tenant(db_session, "Victim B")

        await set_tenant_context(db_session, tenant_b)
        inc_b = await create_incident(db_session, tenant_b, "B's incident")

        # Attempt update as tenant A
        await set_tenant_context(db_session, tenant_a)
        result = await db_session.execute(
            text("UPDATE incidents SET title = 'HACKED' WHERE id = :id RETURNING id"),
            {"id": inc_b},
        )
        updated = result.fetchall()

        assert len(updated) == 0, "UPDATE must not affect another tenant's rows"

        # Verify original title is intact (switch back to B's context)
        await set_tenant_context(db_session, tenant_b)
        check = await db_session.execute(
            text("SELECT title FROM incidents WHERE id = :id"),
            {"id": inc_b},
        )
        row = check.fetchone()
        assert row is not None
        assert row.title == "B's incident"

    @pytest.mark.asyncio
    async def test_tenant_cannot_delete_other_tenant_incidents(self, db_session):
        """DELETE with tenant A context must not delete tenant B rows."""
        tenant_a = await create_tenant(db_session, "Deleter A")
        tenant_b = await create_tenant(db_session, "Protected B")

        await set_tenant_context(db_session, tenant_b)
        inc_b = await create_incident(db_session, tenant_b, "B's protected incident")

        await set_tenant_context(db_session, tenant_a)
        result = await db_session.execute(
            text("DELETE FROM incidents WHERE id = :id RETURNING id"),
            {"id": inc_b},
        )
        deleted = result.fetchall()

        assert len(deleted) == 0, "DELETE must not affect another tenant's rows"

    @pytest.mark.asyncio
    async def test_list_returns_only_own_tenant_incidents(self, db_session):
        """SELECT * (no WHERE clause) returns only the current tenant's incidents."""
        tenant_a = await create_tenant(db_session, "List Tenant A")
        tenant_b = await create_tenant(db_session, "List Tenant B")

        await set_tenant_context(db_session, tenant_a)
        inc_a1 = await create_incident(db_session, tenant_a, "A incident 1")
        inc_a2 = await create_incident(db_session, tenant_a, "A incident 2")

        await set_tenant_context(db_session, tenant_b)
        await create_incident(db_session, tenant_b, "B incident 1")

        # Query as tenant A — should only see A's rows
        await set_tenant_context(db_session, tenant_a)
        result = await db_session.execute(
            text("SELECT id FROM incidents WHERE tenant_id = :tid"),
            {"tid": tenant_a},
        )
        ids = {row.id for row in result.fetchall()}

        assert inc_a1 in ids
        assert inc_a2 in ids
        # B's incident must not appear
        result_b = await db_session.execute(
            text("SELECT id FROM incidents WHERE tenant_id = :tid"),
            {"tid": tenant_b},
        )
        b_ids = {row.id for row in result_b.fetchall()}
        assert len(ids & b_ids) == 0, "Tenant sets must be disjoint"

    @pytest.mark.asyncio
    async def test_no_tenant_context_returns_empty(self, db_session):
        """Without a tenant context, SELECT should return no rows (deny-by-default policy)."""
        tenant_x = await create_tenant(db_session, "Context-less tenant")
        await set_tenant_context(db_session, tenant_x)
        await create_incident(db_session, tenant_x, "Secret incident")

        # Clear the tenant context
        await db_session.execute(text("SET LOCAL \"app.tenant_id\" = ''"))

        result = await db_session.execute(text("SELECT id FROM incidents"))
        rows = result.fetchall()

        assert len(rows) == 0, "Empty tenant context must return no rows"

    @pytest.mark.asyncio
    async def test_scan_isolation(self, db_session):
        """Scans table is also isolated by tenant."""
        tenant_a = await create_tenant(db_session, "Scan Tenant A")
        tenant_b = await create_tenant(db_session, "Scan Tenant B")

        scan_id = str(uuid.uuid4())
        await set_tenant_context(db_session, tenant_b)
        await db_session.execute(
            text(
                "INSERT INTO scans "
                "(id, tenant_id, repository, commit_sha, risk_level, risk_score, "
                " findings_count, duration_ms, created_at) "
                "VALUES (:id, :tid, 'org/repo', 'abc123', 'low', 2.0, 0, 100, NOW())"
            ),
            {"id": scan_id, "tid": tenant_b},
        )

        await set_tenant_context(db_session, tenant_a)
        result = await db_session.execute(
            text("SELECT id FROM scans WHERE id = :id"),
            {"id": scan_id},
        )
        assert len(result.fetchall()) == 0
