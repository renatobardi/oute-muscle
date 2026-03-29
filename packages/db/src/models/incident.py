"""Incident SQLAlchemy model.

Stores documented production incidents with embeddings, version control, and soft delete.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from .base import Base


class Incident(Base):
    """Incident model — core business object linking to detection rules."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Core content
    title = Column(String(500), nullable=False)
    date = Column("date", type_=None, nullable=True)
    source_url = Column(String(2048), nullable=True, unique=True, index=True)
    organization = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, index=True)  # unsafe-regex, race-condition, etc.
    subcategory = Column(String(100), nullable=True)
    failure_mode = Column(Text, nullable=True)
    severity = Column(String(50), nullable=False, index=True)  # critical, high, medium, low
    affected_languages = Column(ARRAY(String(50)), default=list, nullable=False)
    anti_pattern = Column(Text, nullable=False)
    code_example = Column(Text, nullable=True)
    remediation = Column(Text, nullable=False)
    tags = Column(ARRAY(String(100)), default=list, nullable=False)

    # Vector embedding (768 dimensions for text-embedding-005)
    embedding = Column(Vector(768), nullable=True, index=True)

    # Rule linkage
    static_rule_possible = Column("static_rule_possible", type_=None, default=False, nullable=False)
    semgrep_rule_id = Column(String(50), nullable=True, index=True)

    # Version control for optimistic locking
    version = Column(Integer, nullable=False, default=1)

    # Soft delete
    deleted_at = Column("deleted_at", type_=None, nullable=True, index=True)

    __table_args__ = (
        # HNSW index for vector similarity search
        # Note: Created explicitly in migration, not in ORM
        CheckConstraint(
            "version >= 1",
            name="check_incident_version_positive",
        ),
        # RLS policy will be enforced at query time
        # (tenant_id = current_setting('app.tenant_id')::uuid OR tenant_id IS NULL)
        # AND deleted_at IS NULL
    )

    def __repr__(self) -> str:
        return f"<Incident(id={self.id}, title={self.title[:30]}..., version={self.version})>"
