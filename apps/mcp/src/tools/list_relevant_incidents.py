"""list_relevant_incidents MCP tool.

Input: { query: str | None, category: str | None, max_results: int = 10, tenant_id: str }
Output: { incidents: list[dict], total: int }

Each incident dict: { id, title, category, severity, anti_pattern, remediation, source_url | null }
"""

from __future__ import annotations

from typing import Any

from apps.mcp.src.metering import MeteringService


async def list_relevant_incidents(
    query: str | None,
    category: str | None,
    max_results: int,
    tenant_id: str,
    user_id: str,
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """List incidents relevant to code or query.

    Args:
        query: Optional semantic search query
        category: Optional category filter
        max_results: Maximum number of results
        tenant_id: Tenant identifier
        user_id: User identifier
        metering: Metering service

    Returns:
        Dict with incidents list and total count
    """
    if metering is None:
        metering = MeteringService()

    # Increment metering (no quota check for this tool)
    metering.increment(user_id, "free")

    # Stub implementation
    incidents: list[dict[str, Any]] = []

    if query:
        # Vector search stub
        incidents = await _vector_search(query, tenant_id, max_results)
    else:
        # Text/filter search stub
        incidents = await _list_by_category(category, tenant_id, max_results)

    return {
        "incidents": incidents[:max_results],
        "total": len(incidents),
    }


async def _vector_search(
    query: str, tenant_id: str, max_results: int
) -> list[dict[str, Any]]:
    """Vector search for similar incidents.

    Args:
        query: Search query
        tenant_id: Tenant identifier
        max_results: Max results

    Returns:
        List of incident dicts
    """
    # Stub - would use vector_search port
    if vector_search and hasattr(vector_search, "find_similar"):
        return await vector_search.find_similar(query, tenant_id, max_results)  # type: ignore
    return []


async def _list_by_category(
    category: str | None, tenant_id: str, max_results: int
) -> list[dict[str, Any]]:
    """List incidents by category.

    Args:
        category: Category filter
        tenant_id: Tenant identifier
        max_results: Max results

    Returns:
        List of incident dicts
    """
    # Stub - would use incident_repo port
    if incident_repo and hasattr(incident_repo, "list_by_category"):
        return await incident_repo.list_by_category(category, tenant_id, max_results)  # type: ignore
    return []


# Stubs for ports (would be injected in real implementation)
vector_search = None
incident_repo = None
