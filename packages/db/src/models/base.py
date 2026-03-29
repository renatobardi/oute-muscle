"""SQLAlchemy base model with RLS-aware session management.

Constitution VI: Row-Level Security (RLS) policies enforce tenant isolation.
All queries must set current_setting('app.tenant_id') via session factory.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Base model for all SQLAlchemy entities.

    Provides common fields (id, created_at, updated_at) and RLS support.
    """

    __allow_unmapped__ = True

    @declared_attr
    def __tablename__(cls) -> str:  # noqa: N805
        """Convert class name to snake_case table name."""
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Any = Column("created_at", type_=None, nullable=False, default=datetime.utcnow)
    updated_at: Any = Column(
        "updated_at", type_=None, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
