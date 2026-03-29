"""Tenant SQLAlchemy model.

A tenant is a customer of the Oute Muscle platform (multi-tenancy).
"""

import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Tenant(Base):
    """Tenant model representing a customer/organization."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    plan_tier = Column(String(50), nullable=False, default="free")
    is_active = Column("is_active", type_=None, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, plan_tier={self.plan_tier})>"
