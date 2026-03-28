"""get_incident_advisory MCP tool.

Input: { code: str, context: str | None, tenant_id: str }
Output: { advisory_text: str, confidence: float, incident_ids: list[str], model_used: str }

Uses RAGPipeline (stub if no GCP credentials).
"""

from __future__ import annotations

from typing import Any

from apps.mcp.src.metering import MeteringService, QuotaExceededError


async def get_incident_advisory(
    code: str,
    context: str | None,
    tenant_id: str,
    user_id: str,
    tier: str = "free",
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """Get RAG-based advisory for code.

    Args:
        code: Code to analyze
        context: Optional context
        tenant_id: Tenant identifier
        user_id: User identifier
        tier: User tier
        metering: Metering service

    Returns:
        Dict with advisory_text, confidence, incident_ids, model_used

    Raises:
        QuotaExceededError: If user quota exceeded
    """
    if metering is None:
        metering = MeteringService()

    # Check quota
    if not metering.quota_ok(user_id, tier):
        limit = 50 if tier == "free" else (500 if tier == "team" else None)
        current = metering.get_count(user_id)
        raise QuotaExceededError(user_id, limit, current)

    # Increment metering
    metering.increment(user_id, tier)

    # Stub RAG pipeline (would use real pipeline with GCP)
    # For now just return a basic advisory
    result = {
        "advisory_text": "No advisory available",
        "confidence": 0.3,
        "incident_ids": [],
        "model_used": "fallback",
    }

    return {
        "advisory_text": result.get("advisory_text", ""),
        "confidence": result.get("confidence", 0.3),
        "incident_ids": result.get("incident_ids", []),
        "model_used": result.get("model_used", "claude-3-sonnet"),
    }
