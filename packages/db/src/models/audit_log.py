"""AuditLogEntry SQLAlchemy model.

Immutable audit log — records all mutations (INSERT only, never UPDATE/DELETE).
"""

import uuid

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class AuditLogEntry(Base):
    """AuditLogEntry model — immutable audit log for all mutations."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What happened
    action = Column(String(50), nullable=False, index=True)
    # create, update, delete, soft_delete, hard_delete, approve, disable
    entity_type = Column(String(50), nullable=False, index=True)  # incident, rule, scan, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Who did it
    performed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What changed (before/after)
    changes = Column(JSONB, nullable=False)  # {before: {...}, after: {...}}

    def __repr__(self) -> str:
        return (
            f"<AuditLogEntry(id={self.id}, action={self.action}, entity_type={self.entity_type})>"
        )
