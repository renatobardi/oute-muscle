"""User SQLAlchemy model.

Users belong to tenants and have role-based access control.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class User(Base):
    """User model representing a platform user."""

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Any = Column(String(255), nullable=False, unique=True, index=True)
    name: Any = Column(String(255), nullable=False)
    role: Any = Column(String(50), nullable=False, default="viewer")  # viewer, editor, admin
    is_active: Any = Column("is_active", type_=None, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
