"""Advisory SQLAlchemy model.

An Advisory is a consultive recommendation from Layer 2 (RAG + LLM).
"""

import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Advisory(Base):
    """Advisory model — consultive recommendation from Layer 2 RAG."""

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

    # Recommendation content
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incident.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence = Column("confidence", type_=None, nullable=False)  # 0.0-1.0
    reasoning = Column(Text, nullable=False)  # Why this incident is relevant
    remediation_notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Advisory(id={self.id}, incident_id={self.incident_id}, confidence={self.confidence})>"
