"""Incident domain service.

Orchestrates incident creation, updates, deletion with embedding generation,
optimistic locking, and soft delete enforcement.
"""

from __future__ import annotations

import uuid

from ...ports.embedding import EmbeddingPort
from ...ports.incident_repo import IncidentRepoPort
from ...ports.vector_search import VectorSearchPort
from .entity import Incident
from .enums import IncidentCategory, IncidentSeverity


class IncidentService:
    """Domain service for incident management."""

    def __init__(
        self,
        incident_repo: IncidentRepoPort,
        embedding_adapter: EmbeddingPort,
        vector_search: VectorSearchPort,
    ) -> None:
        """Initialize service with ports."""
        self.incident_repo = incident_repo
        self.embedding_adapter = embedding_adapter
        self.vector_search = vector_search

    async def create_incident(
        self, incident: Incident
    ) -> Incident:
        """Create a new incident with embedding generation.

        Args:
            incident: Incident without embedding set.

        Returns:
            Created incident with embedding and DB timestamps.

        Raises:
            DuplicateSourceUrlError: If source_url already exists.
        """
        # Generate embedding from title + anti_pattern
        embedding_text = f"{incident.title} {incident.anti_pattern}"
        embedding = await self.embedding_adapter.embed(embedding_text)

        # Set embedding and persist
        incident_with_embedding = incident.with_embedding(embedding)
        return await self.incident_repo.create(incident_with_embedding)

    async def update_incident(
        self, incident: Incident, *, expected_version: int
    ) -> Incident:
        """Update an incident with optimistic locking and re-embedding.

        Args:
            incident: Updated incident (version must be expected_version + 1).
            expected_version: Expected current version in DB.

        Returns:
            Updated incident with new embedding.

        Raises:
            OptimisticLockError: If DB version != expected_version.
        """
        # Re-generate embedding if anti_pattern changed
        embedding_text = f"{incident.title} {incident.anti_pattern}"
        embedding = await self.embedding_adapter.embed(embedding_text)
        incident_with_embedding = incident.with_embedding(embedding)

        return await self.incident_repo.update(
            incident_with_embedding, expected_version=expected_version
        )

    async def soft_delete_incident(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        """Soft-delete an incident (sets deleted_at).

        Fails if incident has an active semgrep_rule_id.

        Args:
            incident_id: ID of incident to delete.
            tenant_id: Tenant context.

        Raises:
            IncidentHasActiveRuleError: If incident has active rule.
        """
        await self.incident_repo.soft_delete(incident_id, tenant_id=tenant_id)

    async def hard_delete_incident(
        self, incident_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        """Permanently delete an incident (CLI only).

        Args:
            incident_id: ID of incident to delete.
            tenant_id: Tenant context.
        """
        await self.incident_repo.hard_delete(incident_id, tenant_id=tenant_id)

    async def list_incidents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        category: IncidentCategory | None = None,
        severity: IncidentSeverity | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Incident]:
        """List incidents with optional filtering."""
        return await self.incident_repo.list(
            tenant_id=tenant_id,
            category=category,
            severity=severity,
            limit=limit,
            offset=offset,
            include_deleted=False,
        )

    async def search_incidents(
        self,
        query: str,
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 20,
        use_semantic: bool = False,
    ) -> list[Incident]:
        """Search incidents by keyword or semantic similarity.

        Args:
            query: Search query (or text to embed for semantic search).
            tenant_id: Restrict to tenant.
            limit: Max results.
            use_semantic: If True, embed query and search by vector similarity.

        Returns:
            List of matching incidents.
        """
        if use_semantic:
            # Embed query and search by vector similarity
            embedding = await self.embedding_adapter.embed(query)
            return await self.vector_search.find_similar(
                embedding, tenant_id=tenant_id, limit=limit
            )
        else:
            # Full-text search
            return await self.incident_repo.search(
                query, tenant_id=tenant_id, limit=limit
            )
