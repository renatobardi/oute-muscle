"""SemgrepRule SQLAlchemy model.

Stores Semgrep rules linked to incidents with revision tracking.
"""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class SemgrepRule(Base):
    """SemgrepRule model — Semgrep rules linked to incidents."""

    id = Column(String(50), primary_key=True)  # e.g. "unsafe-regex-001"
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incident.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Semgrep rule content
    category = Column(String(50), nullable=False, index=True)  # unsafe-regex, race-condition, etc.
    sequence_number = Column(Integer, nullable=False, default=1)  # next sequence within category
    yaml_content = Column(Text, nullable=False)  # Full YAML rule definition
    test_file_content = Column(Text, nullable=False)  # Test cases (Semgrep format)
    languages = Column(
        "languages", type_=None, default=list, nullable=False
    )  # [python, javascript, ...]
    severity = Column(String(50), nullable=False)  # error, warning, info (Semgrep severity)
    message = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, default="manual")  # manual, synthesized

    # Metadata
    is_approved = Column("is_approved", type_=None, default=False, nullable=False)
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at = Column("approved_at", type_=None, nullable=True)
    is_active = Column("is_active", type_=None, default=True, nullable=False)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # False positive tracking (FR-028: auto-disable at threshold 3)
    false_positive_count = Column(Integer, nullable=False, default=0)
    auto_disabled = Column("auto_disabled", type_=None, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "sequence_number >= 1",
            name="check_rule_sequence_positive",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SemgrepRule(id={self.id}, category={self.category}, is_approved={self.is_approved})>"
        )
