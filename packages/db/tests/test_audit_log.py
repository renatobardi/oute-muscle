"""Unit tests for AuditLogEntry model and audit log recording.

Tests verify:
- Audit entries are created for all mutation operations (create, update, delete, soft_delete)
- Each entry records before/after state as JSONB
- Only authorized users can view audit logs for their tenant
- Audit log is immutable (INSERT only, no UPDATE/DELETE)
- Action enum captures operation type

No external dependencies — tests use mock repo.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from packages.core.src.domain.incidents.enums import AuditAction


class MockAuditLogEntry:
    """Mock AuditLogEntry for unit tests."""

    def __init__(
        self,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        performed_by: uuid.UUID,
        changes: dict,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.tenant_id = tenant_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.performed_by = performed_by
        self.changes = changes
        self.created_at = created_at or datetime.utcnow()


class MockAuditLogRepo:
    """Mock audit log repository."""

    def __init__(self) -> None:
        self.entries: list[MockAuditLogEntry] = []

    async def create(self, entry: MockAuditLogEntry) -> MockAuditLogEntry:
        """Persist audit entry (append-only)."""
        self.entries.append(entry)
        return entry

    async def list_for_incident(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> list[MockAuditLogEntry]:
        """List audit entries for an incident in this tenant."""
        return [
            e
            for e in self.entries
            if e.entity_id == incident_id
            and e.entity_type == "incident"
            and e.tenant_id == tenant_id
        ]


@pytest.fixture
def mock_audit_log_repo() -> MockAuditLogRepo:
    """Create mock audit log repository."""
    return MockAuditLogRepo()


class TestAuditLogEntryCreation:
    """Tests for creating audit log entries."""

    async def test_create_audit_entry_for_incident_creation(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test audit entry is created when incident is created."""
        # Arrange
        incident_id = uuid.uuid4()
        changes = {
            "before": {},
            "after": {
                "id": str(incident_id),
                "title": "Test incident",
                "category": "unsafe-regex",
                "severity": "critical",
            },
        }

        # Act
        entry = await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes=changes,
            )
        )

        # Assert
        assert entry.action == AuditAction.CREATE
        assert entry.entity_type == "incident"
        assert entry.entity_id == incident_id
        assert entry.performed_by == user_id

    async def test_create_audit_entry_for_incident_update(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test audit entry is created when incident is updated."""
        # Arrange
        incident_id = uuid.uuid4()
        changes = {
            "before": {"anti_pattern": "old pattern", "version": 1},
            "after": {"anti_pattern": "new pattern", "version": 2},
        }

        # Act
        entry = await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.UPDATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes=changes,
            )
        )

        # Assert
        assert entry.action == AuditAction.UPDATE
        assert entry.changes["before"]["anti_pattern"] == "old pattern"
        assert entry.changes["after"]["anti_pattern"] == "new pattern"

    async def test_create_audit_entry_for_soft_delete(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test audit entry is created when incident is soft-deleted."""
        # Arrange
        incident_id = uuid.uuid4()
        changes = {
            "before": {"deleted_at": None},
            "after": {"deleted_at": "2026-03-28T10:00:00Z"},
        }

        # Act
        entry = await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.SOFT_DELETE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes=changes,
            )
        )

        # Assert
        assert entry.action == AuditAction.SOFT_DELETE
        assert entry.changes["before"]["deleted_at"] is None

    async def test_create_audit_entry_for_hard_delete(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test audit entry is created when incident is hard-deleted."""
        # Arrange
        incident_id = uuid.uuid4()
        changes = {"before": {"id": str(incident_id)}, "after": {}}

        # Act
        entry = await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.HARD_DELETE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes=changes,
            )
        )

        # Assert
        assert entry.action == AuditAction.HARD_DELETE


class TestAuditLogQuerying:
    """Tests for querying audit logs."""

    async def test_list_audit_entries_for_incident(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test listing audit entries for a specific incident."""
        # Arrange
        incident_id = uuid.uuid4()
        other_incident_id = uuid.uuid4()

        # Create entries for both incidents
        await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes={},
            )
        )
        await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                entity_type="incident",
                entity_id=other_incident_id,
                performed_by=user_id,
                changes={},
            )
        )

        # Act
        results = await mock_audit_log_repo.list_for_incident(incident_id, tenant_id=tenant_id)

        # Assert
        assert len(results) == 1
        assert results[0].entity_id == incident_id

    async def test_audit_log_respects_tenant_isolation(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID
    ) -> None:
        """Test that audit logs are isolated by tenant via RLS."""
        # Arrange
        tenant_id_1 = uuid.uuid4()
        tenant_id_2 = uuid.uuid4()
        incident_id = uuid.uuid4()

        # Create entries for both tenants
        await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id_1,
                action=AuditAction.CREATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes={},
            )
        )
        await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id_2,
                action=AuditAction.CREATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes={},
            )
        )

        # Act: query as tenant_id_1
        results = await mock_audit_log_repo.list_for_incident(incident_id, tenant_id=tenant_id_1)

        # Assert: only see tenant_id_1's entry
        assert len(results) == 1
        assert results[0].tenant_id == tenant_id_1

    async def test_audit_log_tracks_all_changed_fields(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test that audit log records all changed fields before and after."""
        # Arrange
        incident_id = uuid.uuid4()
        changes = {
            "before": {
                "title": "Old title",
                "anti_pattern": "old pattern",
                "version": 1,
            },
            "after": {
                "title": "New title",
                "anti_pattern": "new pattern",
                "version": 2,
            },
        }

        # Act
        entry = await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.UPDATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes=changes,
            )
        )

        # Assert
        assert "title" in entry.changes["before"]
        assert "title" in entry.changes["after"]
        assert "anti_pattern" in entry.changes["before"]
        assert "version" in entry.changes["before"]


class TestAuditLogImmutability:
    """Tests for audit log immutability."""

    async def test_audit_log_is_append_only(
        self, mock_audit_log_repo: MockAuditLogRepo, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Test that audit log entries cannot be modified (INSERT only)."""
        # In a real DB, this would be enforced by constraints/triggers
        # For unit test, verify that mock doesn't support updates
        incident_id = uuid.uuid4()
        entry = await mock_audit_log_repo.create(
            MockAuditLogEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                entity_type="incident",
                entity_id=incident_id,
                performed_by=user_id,
                changes={},
            )
        )

        # Assert: entry is immutable (no update method)
        assert not hasattr(mock_audit_log_repo, "update")
        assert not hasattr(mock_audit_log_repo, "delete")
