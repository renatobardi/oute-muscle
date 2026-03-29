"""FastAPI dependency injection helpers — per-request resources.

These are used via Annotated[X, Depends(get_x)] in route handlers.

Pattern:
  - App-level singletons (session factory, LLM adapters) live in DIContainer (main.py)
  - Per-request resources (DB session, domain services) are created here via Depends
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.main import get_container

# ---------------------------------------------------------------------------
# Database session — one per request, tenant-scoped
# ---------------------------------------------------------------------------


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a tenant-scoped AsyncSession for the current request."""
    container = get_container()
    async for session in container.session_factory.get_session():
        yield session


# ---------------------------------------------------------------------------
# Domain services — constructed per-request with the current DB session
# ---------------------------------------------------------------------------


def get_incident_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Construct IncidentService with per-request DB session."""
    from packages.core.src.domain.incidents.service import IncidentService
    from packages.db.src.adapters.pg_incident_repo import PostgreSQLIncidentRepo
    from packages.db.src.adapters.pg_vector_search import PostgreSQLVectorSearch

    container = get_container()

    repo = PostgreSQLIncidentRepo(session)
    vector_search = PostgreSQLVectorSearch(session)

    return IncidentService(
        incident_repo=repo,
        embedding_adapter=container.embedding_adapter,
        vector_search=vector_search,
    )


# ---------------------------------------------------------------------------
# Type aliases for route signatures
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
