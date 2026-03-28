"""PostgreSQL session factory with tenant context (RLS support).

Constitution VI: Row-Level Security policies enforce tenant isolation.
Every session must SET LOCAL "app.tenant_id" before querying.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


class TenantContextSession(AsyncSession):
    """AsyncSession with tenant context awareness for RLS.

    Usage:
        async with TenantContextSession(engine, tenant_id) as session:
            # All queries within this session are RLS-scoped to tenant_id
            incidents = await session.execute(select(Incident))
    """

    def __init__(self, *args, tenant_id: uuid.UUID | None = None, **kwargs):  # type: ignore[no-untyped-def]
        """Initialize session with optional tenant context."""
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id

    async def __aenter__(self) -> TenantContextSession:
        """Enter context manager and set tenant context."""
        if self.tenant_id:
            # SET LOCAL is transaction-scoped, will be cleared on commit/rollback
            await self.execute(
                f"SET LOCAL app.tenant_id = '{self.tenant_id}'"  # type: ignore[arg-type]
            )
        return self

    async def __aexit__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Exit context manager."""
        await super().__aexit__(*args, **kwargs)


class SessionFactory:
    """Factory for creating tenant-aware database sessions."""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        """Initialize session factory.

        Args:
            database_url: asyncpg connection string (e.g. postgresql+asyncpg://...)
            echo: If True, log all SQL statements
        """
        self.engine = create_async_engine(
            database_url,
            echo=echo,
            poolclass=NullPool,  # One conn per request for simplicity
            connect_args={
                "server_settings": {
                    "application_name": "oute-muscle-api",
                    "jit": "off",  # Disable JIT for predictable query planning
                }
            },
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=TenantContextSession,
            expire_on_commit=False,
        )

    async def get_session(
        self, tenant_id: uuid.UUID | None = None
    ) -> AsyncGenerator[TenantContextSession, None]:
        """Get a new session with optional tenant context.

        Args:
            tenant_id: If provided, RLS policies will scope to this tenant.

        Yields:
            TenantContextSession with tenant context pre-configured.
        """
        async with self.async_session(tenant_id=tenant_id) as session:
            yield session

    async def close(self) -> None:
        """Close all connections in the pool."""
        await self.engine.dispose()
