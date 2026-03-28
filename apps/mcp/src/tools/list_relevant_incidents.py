"""list_relevant_incidents MCP tool — real DB queries.

Input:  { query: str | None, category: str | None, max_results: int = 10, tenant_id: str }
Output: { incidents: list[dict], total: int }

Each incident dict:
    { id, title, category, severity, anti_pattern, remediation, source_url | null }

When query is provided, uses vector similarity search (embedding-based).
Without a query, returns incidents filtered by category (or all if None).
Falls back gracefully when DATABASE_URL is not configured.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from apps.mcp.src.metering import MeteringService

logger = logging.getLogger(__name__)


async def list_relevant_incidents(
    query: str | None,
    category: str | None,
    max_results: int,
    tenant_id: str,
    user_id: str,
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """List incidents relevant to a query or category.

    When query is set: embeds the query and runs vector similarity search.
    When only category is set: filters by category with limit.
    When neither is set: returns the most recent incidents.

    Args:
        query: Optional natural-language search query.
        category: Optional category slug (e.g. 'unsafe-regex').
        max_results: Maximum number of incidents to return (1–50).
        tenant_id: Tenant UUID string for RLS scoping.
        user_id: User identifier for metering.
        metering: MeteringService instance (created fresh if None).

    Returns:
        Dict with keys:
            incidents – list of incident dicts
            total     – number of incidents returned
    """
    if metering is None:
        metering = MeteringService()

    # list_relevant_incidents has no quota restriction — increment only
    metering.increment(user_id, "free")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.info("list_relevant_incidents_fallback", reason="DATABASE_URL not set")
        return {"incidents": [], "total": 0}

    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        tid = uuid.UUID("00000000-0000-0000-0000-000000000001")

    max_results = max(1, min(max_results, 50))

    try:
        if query:
            incidents = await _semantic_search(
                query=query,
                tenant_id=tid,
                limit=max_results,
                database_url=database_url,
            )
        else:
            incidents = await _filter_list(
                category=category,
                tenant_id=tid,
                limit=max_results,
                database_url=database_url,
            )
    except Exception as exc:
        logger.warning("list_relevant_incidents_db_error", error=str(exc))
        return {"incidents": [], "total": 0}

    return {"incidents": incidents[:max_results], "total": len(incidents)}


async def _semantic_search(
    *,
    query: str,
    tenant_id: uuid.UUID,
    limit: int,
    database_url: str,
) -> list[dict[str, Any]]:
    """Embed query and retrieve similar incidents via pgvector.

    Args:
        query: Natural-language query string.
        tenant_id: Tenant UUID for RLS scoping.
        limit: Maximum results.
        database_url: PostgreSQL connection string.

    Returns:
        List of normalised incident dicts.
    """
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not gcp_project:
        # No GCP — fall back to keyword search
        logger.info("semantic_search_fallback_no_gcp")
        return await _filter_list(
            category=None,
            tenant_id=tenant_id,
            limit=limit,
            database_url=database_url,
        )

    vertex_location = os.environ.get("VERTEX_LOCATION", "us-central1")

    from apps.api.src.adapters.vertex_embedding import VertexAIEmbedding
    from packages.db.src.adapters.pg_vector_search import PostgreSQLVectorSearch
    from packages.db.src.session import SessionFactory

    session_factory = SessionFactory(database_url=database_url)
    try:
        async for session in session_factory.get_session(tenant_id=tenant_id):
            embedding_adapter = VertexAIEmbedding(
                project_id=gcp_project, location=vertex_location
            )
            query_embedding = await embedding_adapter.embed(query)

            if not query_embedding:
                return []

            vector_search = PostgreSQLVectorSearch(session)
            results = await vector_search.find_similar(
                query_embedding,
                tenant_id=tenant_id,
                limit=limit,
                min_similarity=0.5,
            )
            return [_entity_to_dict(r.incident) for r in results]
    finally:
        await session_factory.close()

    return []


async def _filter_list(
    *,
    category: str | None,
    tenant_id: uuid.UUID,
    limit: int,
    database_url: str,
) -> list[dict[str, Any]]:
    """List incidents filtered by category (or all) from the DB.

    Args:
        category: Optional category filter.
        tenant_id: Tenant UUID for RLS scoping.
        limit: Maximum results.
        database_url: PostgreSQL connection string.

    Returns:
        List of normalised incident dicts.
    """
    from packages.db.src.adapters.pg_incident_repo import PostgreSQLIncidentRepo
    from packages.db.src.session import SessionFactory

    category_enum = None
    if category:
        try:
            from packages.core.src.domain.incidents.enums import IncidentCategory

            category_enum = IncidentCategory(category)
        except ValueError:
            logger.warning("list_incidents_unknown_category", category=category)

    session_factory = SessionFactory(database_url=database_url)
    try:
        async for session in session_factory.get_session(tenant_id=tenant_id):
            repo = PostgreSQLIncidentRepo(session)
            entities = await repo.list(
                category=category_enum,
                severity=None,
                limit=limit,
                offset=0,
            )
            return [_entity_to_dict(e) for e in entities]
    finally:
        await session_factory.close()

    return []


def _entity_to_dict(incident: Any) -> dict[str, Any]:
    """Convert a domain Incident entity to the MCP tool output format.

    Args:
        incident: Domain Incident entity.

    Returns:
        Normalised incident dict for MCP tool output.
    """
    return {
        "id": str(incident.id),
        "title": incident.title,
        "category": str(incident.category.value) if incident.category else None,
        "severity": str(incident.severity.value) if incident.severity else None,
        "anti_pattern": incident.anti_pattern,
        "remediation": incident.remediation,
        "source_url": incident.source_url,
    }
