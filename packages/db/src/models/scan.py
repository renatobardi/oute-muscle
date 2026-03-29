"""Scan SQLAlchemy model.

A Scan represents one run of Semgrep on a codebase (Layer 1) or evaluation via RAG (Layer 2).
"""

import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Scan(Base):
    """Scan model — results of running Semgrep on a codebase."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Trigger
    trigger_source = Column(
        String(50), nullable=False
    )  # github_push, github_pr, mcp, rest_api, pre_commit
    repository = Column(String(1024), nullable=False)  # org/repo
    pr_number = Column(Integer, nullable=True)  # NULL if not a PR

    # Code context
    commit_sha = Column(String(40), nullable=False, index=True)
    diff_lines = Column(Integer, nullable=False, default=0)

    # Results
    layer1_findings_count = Column(Integer, nullable=False, default=0)
    risk_score = Column(Integer, nullable=True)  # 0-100; NULL until completed
    risk_level = Column(String(20), nullable=True)  # low, medium, high, critical
    duration_ms = Column(Integer, nullable=False, default=0)

    # Status
    status = Column(
        String(50), nullable=False, default="running"
    )  # running, completed, failed, timeout
    completed_at = Column("completed_at", type_=None, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="check_scan_risk_score_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, repository={self.repository}, status={self.status})>"
