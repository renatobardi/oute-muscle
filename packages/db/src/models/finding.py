"""Finding SQLAlchemy model.

A Finding is a single match of a Semgrep rule in source code (output of Layer 1).
"""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Finding(Base):
    """Finding model — a single Semgrep rule match in source code."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule reference
    rule_id = Column(String(50), nullable=False, index=True)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incident.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Code location
    file_path = Column(String(1024), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    # Finding details
    severity = Column(String(50), nullable=False)  # critical, high, medium, low
    message = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)

    # False positive tracking (FR-028)
    status = Column(String(50), nullable=False, default="open")  # open, false_positive
    false_positive_count = Column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, rule_id={self.rule_id}, file_path={self.file_path}:{self.start_line})>"
