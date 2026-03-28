"""SynthesisCandidate SQLAlchemy model.

Layer 3 auto-generated rule candidates awaiting approval (enterprise only).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class SynthesisCandidate(Base):
    """SynthesisCandidate model — auto-generated Semgrep rule candidate."""

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source
    incident_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("incident.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Generated rule
    proposed_rule_id: Any = Column(String(50), nullable=False)  # e.g. "unsafe-regex-002"
    yaml_content: Any = Column(Text, nullable=False)  # Proposed Semgrep YAML
    test_file_content: Any = Column(Text, nullable=False)  # Proposed test cases
    languages: Any = Column("languages", type_=None, default=list, nullable=False)

    # Status and approval
    status: Any = Column(String(50), nullable=False, default="pending")
    # pending, approved, rejected, archived, failed
    reviewed_by: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Any = Column("reviewed_at", type_=None, nullable=True)
    review_notes: Any = Column(Text, nullable=True)

    # Metadata
    confidence: Any = Column("confidence", type_=None, nullable=False, default=0.0)  # 0.0-1.0
    reasoning: Any = Column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<SynthesisCandidate(id={self.id}, proposed_rule_id={self.proposed_rule_id}, status={self.status})>"
