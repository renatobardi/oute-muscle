"""User SQLAlchemy model.

Users belong to tenants and have role-based access control.
Firebase UID links to the shared oute-488706 Firebase Auth user pool.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class User(Base):
    """User model representing a platform user."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")  # viewer, editor, admin
    is_active = Column("is_active", type_=None, nullable=False, default=True)

    # Firebase Auth integration (spec 237)
    firebase_uid = Column(String(128), nullable=True, unique=True, index=True)
    display_name = Column(String(255), nullable=True)
    email_verified = Column("email_verified", type_=None, nullable=False, default=False)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
