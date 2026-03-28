"""Integration tests for PostgreSQL incident repository.

Tests verify:
- CRUD operations on real PostgreSQL (using test database)
- Optimistic locking with version column
- Soft delete with deleted_at timestamp
- RLS tenant isolation
- Unique constraint on source_url

Requires: DATABASE_URL env var pointing to test PostgreSQL instance.
"""

from __future__ import annotations

import uuid

import pytest
from src.domain.incidents.entity import Incident

# Skip these tests if DATABASE_URL is not set
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestPostgreSQLIncidentRepo:
    """Integration tests for PostgreSQL incident repository.

    NOTE: These tests require a test PostgreSQL database to be running.
    Use pytest -m integration to run these tests.
    """

    async def test_create_incident_stores_in_database(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test that incident is stored and can be retrieved."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_get_by_id_retrieves_stored_incident(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test get_by_id returns stored incident with all fields intact."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_duplicate_source_url_raises_error(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test that duplicate source_url raises DuplicateSourceUrlError."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_optimistic_locking_succeeds_with_matching_version(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test update succeeds when expected_version matches DB version."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_optimistic_locking_fails_with_mismatched_version(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test update fails when expected_version != DB version (OptimisticLockError)."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_soft_delete_sets_deleted_at(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test soft_delete sets deleted_at timestamp and excludes from list()."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_soft_delete_with_active_rule_fails(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test soft_delete raises IncidentHasActiveRuleError if semgrep_rule_id is set."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_list_respects_tenant_isolation_via_rls(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Test list() respects Row-Level Security (RLS) for tenant isolation."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_list_excludes_deleted_by_default(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test list() excludes soft-deleted incidents unless include_deleted=True."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_list_filters_by_category(self, sample_incident_with_embedding: Incident) -> None:
        """Test list(category=...) filters incidents by category."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_list_filters_by_severity(self, sample_incident_with_embedding: Incident) -> None:
        """Test list(severity=...) filters incidents by severity."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_version_increments_on_update(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test version column increments on each update."""
        pytest.skip("PostgreSQL adapter not yet implemented")

    async def test_embedding_vector_stored_and_retrieved(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test 768-dimensional embedding vector is stored and retrieved correctly."""
        pytest.skip("PostgreSQL adapter not yet implemented")
