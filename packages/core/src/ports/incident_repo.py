"""IncidentRepo port — abstracts PostgreSQL incident storage with optimistic locking."""

from __future__ import annotations

import uuid
from typing import Optional, Protocol, runtime_checkable

from ..domain.incidents.entity import Incident
from ..domain.incidents.enums import IncidentCategory, IncidentSeverity


@runtime_checkable
class IncidentRepoPort(Protocol):
    """Port for incident persistence. Implemented by PostgreSQL adapter."""

    async def create(self, incident: Incident) -> Incident:
        """Persist a new incident.

        Args:
            incident: The incident to create (must have embedding set).

        Returns:
            The created incident (with DB-generated timestamps if applicable).

        Raises:
            DuplicateSourceUrlError: If source_url already exists.
            IncidentRepoError: For other persistence failures.
        """
        ...

    async def get_by_id(
        self, incident_id: uuid.UUID, *, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[Incident]:
        """Retrieve an incident by ID.

        Args:
            incident_id: The incident UUID.
            tenant_id: If provided, restricts to tenant scope (RLS context).

        Returns:
            The incident or None if not found.
        """
        ...

    async def update(self, incident: Incident, *, expected_version: int) -> Incident:
        """Update an incident with optimistic locking.

        Args:
            incident: The updated incident (version must be current + 1).
            expected_version: The version the caller expects in the DB.
                              Update fails if DB version != expected_version.

        Returns:
            The updated incident with incremented version.

        Raises:
            OptimisticLockError: If DB version != expected_version.
            IncidentRepoError: For other failures.
        """
        ...

    async def soft_delete(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        """Soft-delete an incident (sets deleted_at).

        Raises:
            IncidentHasActiveRuleError: If the incident has an active semgrep_rule_id.
            IncidentRepoError: For other failures.
        """
        ...

    async def hard_delete(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        """Permanently delete an incident (CLI --hard-delete only)."""
        ...

    async def list(
        self,
        *,
        tenant_id: Optional[uuid.UUID] = None,
        category: Optional[IncidentCategory] = None,
        severity: Optional[IncidentSeverity] = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[Incident]:
        """List incidents with optional filtering."""
        ...

    async def search(
        self,
        query: str,
        *,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 20,
    ) -> list[Incident]:
        """Full-text search over title, anti_pattern, and remediation."""
        ...


class IncidentRepoError(Exception):
    """Base error for incident repository failures."""


class DuplicateSourceUrlError(IncidentRepoError):
    """Raised when source_url already exists in the database."""


class OptimisticLockError(IncidentRepoError):
    """Raised when optimistic locking detects a concurrent modification."""


class IncidentHasActiveRuleError(IncidentRepoError):
    """Raised when attempting to delete an incident with an active rule."""
