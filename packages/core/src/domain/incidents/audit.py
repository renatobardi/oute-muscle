"""AuditLogService — records before/after diffs for all mutations.

Constitution VII: Immutable audit log for compliance and debugging.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from ...domain.incidents.enums import AuditAction


class AuditLogEntry:
    """Represents a single audit log entry (before/after diff)."""

    def __init__(
        self,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        performed_by: uuid.UUID,
        changes: dict[str, Any],
        created_at: datetime | None = None,
    ) -> None:
        """Initialize audit log entry."""
        self.id = id
        self.tenant_id = tenant_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.performed_by = performed_by
        self.changes = changes  # {before: {...}, after: {...}}
        self.created_at = created_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"<AuditLogEntry(id={self.id}, action={self.action}, entity_type={self.entity_type})>"
        )


class AuditLogService:
    """Domain service for recording audit logs."""

    @staticmethod
    def create_entry(
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        performed_by: uuid.UUID,
        tenant_id: uuid.UUID,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Create an audit log entry for a mutation.

        Args:
            action: Type of action (create, update, delete, etc.)
            entity_type: Type of entity (incident, rule, scan, etc.)
            entity_id: ID of entity.
            performed_by: User who performed the action.
            tenant_id: Tenant context.
            before: State before mutation (None for create).
            after: State after mutation (None for delete).

        Returns:
            AuditLogEntry ready to persist.
        """
        changes = {
            "before": before or {},
            "after": after or {},
        }

        return AuditLogEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            performed_by=performed_by,
            changes=changes,
        )

    @staticmethod
    def compute_diff(before_dict: dict[str, Any], after_dict: dict[str, Any]) -> dict[str, Any]:
        """Compute what changed between before and after dicts.

        Returns:
            {field_name: {before: ..., after: ...}} for changed fields only.
        """
        diff = {}
        all_keys = set(before_dict.keys()) | set(after_dict.keys())

        for key in all_keys:
            before_val = before_dict.get(key)
            after_val = after_dict.get(key)
            if before_val != after_val:
                diff[key] = {"before": before_val, "after": after_val}

        return diff
