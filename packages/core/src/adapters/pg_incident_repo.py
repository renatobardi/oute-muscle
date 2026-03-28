"""PostgreSQL incident repository adapter (IncidentRepoPort implementation).

Constitution VI: Adapter implements port with real PostgreSQL persistence.
Uses optimistic locking (version column), soft delete (deleted_at), and RLS.
"""

from __future__ import annotations

import uuid

from ..domain.incidents.entity import Incident
from ..domain.incidents.enums import IncidentCategory, IncidentSeverity
from ..ports.incident_repo import (
    IncidentRepoPort,
)


class PostgreSQLIncidentRepo(IncidentRepoPort):
    """PostgreSQL adapter for IncidentRepoPort."""

    async def create(self, incident: Incident) -> Incident:
        """Persist a new incident."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def get_by_id(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID | None = None
    ) -> Incident | None:
        """Retrieve an incident by ID."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def update(self, incident: Incident, *, expected_version: int) -> Incident:
        """Update an incident with optimistic locking."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def soft_delete(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        """Soft-delete an incident (sets deleted_at)."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def hard_delete(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        """Permanently delete an incident (CLI --hard-delete only)."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def list(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: IncidentCategory | None = None,
        severity: IncidentSeverity | None = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[Incident]:
        """List incidents with optional filtering."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")

    async def search(
        self,
        query: str,
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[Incident]:
        """Full-text search over title, anti_pattern, and remediation."""
        raise NotImplementedError("PostgreSQL adapter implementation pending")
