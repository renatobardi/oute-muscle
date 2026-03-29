"""get_incident_advisory MCP tool — real RAG pipeline execution.

Input:  { code: str, context: str | None, tenant_id: str }
Output: { advisory_text: str, confidence: float, incident_ids: list[str], model_used: str }

Runs the full RAG pipeline (embed → vector search → LLM) when GCP and
DATABASE_URL are configured.  Falls back to a minimal static response
when prerequisites are missing, so the MCP server remains usable in
local dev without cloud credentials.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from apps.mcp.src.metering import MeteringService, QuotaExceededError

logger = logging.getLogger(__name__)


async def get_incident_advisory(
    code: str,
    context: str | None,
    tenant_id: str,
    user_id: str,
    tier: str = "free",
    metering: MeteringService | None = None,
) -> dict[str, Any]:
    """Get an incident-based advisory for a code snippet via RAG.

    Combines the provided code (and optional context) into a pseudo-diff,
    embeds it, retrieves similar past incidents from the knowledge base,
    and asks the appropriate LLM to generate a security advisory.

    Args:
        code: Code snippet to analyse.
        context: Optional surrounding context or description.
        tenant_id: Tenant UUID string for RLS scoping.
        user_id: User identifier for quota tracking.
        tier: Subscription tier — controls quota and LLM selection.
        metering: MeteringService instance (created fresh if None).

    Returns:
        Dict with keys:
            advisory_text   - LLM-generated advisory (markdown)
            confidence      - float in [0.0, 1.0]
            incident_ids    - list of matched incident UUID strings
            model_used      - model identifier string

    Raises:
        QuotaExceededError: If the user has exceeded their advisory quota.
    """
    if metering is None:
        metering = MeteringService()

    if not metering.quota_ok(user_id, tier):
        limit = 50 if tier == "free" else (500 if tier == "team" else None)
        current = metering.get_count(user_id)
        raise QuotaExceededError(user_id, limit, current)

    metering.increment(user_id, tier)

    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    database_url = os.environ.get("DATABASE_URL")

    if not gcp_project or not database_url:
        logger.info(
            "get_incident_advisory_fallback",
            reason="GCP_PROJECT or DATABASE_URL not set",
        )
        return {
            "advisory_text": (
                "Advisory service not available in local mode. "
                "Configure GOOGLE_CLOUD_PROJECT and DATABASE_URL to enable RAG advisory."
            ),
            "confidence": 0.0,
            "incident_ids": [],
            "model_used": "none",
        }

    # Build pseudo-diff from code + context
    diff_text = _build_diff(code, context)

    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        tid = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Determine risk level from tier (advisory tool uses a fixed level)
    from packages.core.src.domain.incidents.enums import RiskLevel

    risk_level_map = {
        "free": RiskLevel.LOW,
        "team": RiskLevel.MEDIUM,
        "enterprise": RiskLevel.HIGH,
    }
    risk_level = risk_level_map.get(tier, RiskLevel.LOW)

    try:
        advisory_text, confidence, incident_ids, model_used = await _run_rag(
            diff=diff_text,
            tenant_id=tid,
            risk_level=risk_level,
            database_url=database_url,
            gcp_project=gcp_project,
        )
    except Exception as exc:
        logger.warning("get_incident_advisory_rag_error", error=str(exc))
        return {
            "advisory_text": "Advisory generation failed. Please try again.",
            "confidence": 0.0,
            "incident_ids": [],
            "model_used": "error",
        }

    return {
        "advisory_text": advisory_text,
        "confidence": confidence,
        "incident_ids": incident_ids,
        "model_used": model_used,
    }


async def _run_rag(
    *,
    diff: str,
    tenant_id: uuid.UUID,
    risk_level: Any,
    database_url: str,
    gcp_project: str,
) -> tuple[str, float, list[str], str]:
    """Run RAG pipeline and return (advisory_text, confidence, incident_ids, model).

    Opens a new DB session, builds all adapters, runs the pipeline, and
    closes the session factory when done.

    Args:
        diff: Pseudo-diff or code text to analyse.
        tenant_id: Tenant UUID for vector search scoping.
        risk_level: Desired RiskLevel for LLM routing.
        database_url: PostgreSQL connection string.
        gcp_project: GCP project ID.

    Returns:
        Tuple of (advisory_text, confidence, incident_ids, model_used).
    """
    vertex_location = os.environ.get("VERTEX_LOCATION", "us-central1")

    from apps.api.src.adapters.vertex_embedding import VertexAIEmbedding
    from apps.api.src.adapters.vertex_llm import (
        VertexClaudeSonnet,
        VertexGeminiFlash,
        VertexGeminiPro,
    )
    from packages.core.src.domain.advisory.llm_router import LLMRouter
    from packages.core.src.domain.advisory.rag_pipeline import RAGPipeline
    from packages.db.src.adapters.pg_vector_search import PostgreSQLVectorSearch
    from packages.db.src.session import SessionFactory

    session_factory = SessionFactory(database_url=database_url)
    try:
        async for session in session_factory.get_session(tenant_id=tenant_id):
            pipeline = RAGPipeline(
                embedding_port=VertexAIEmbedding(project_id=gcp_project, location=vertex_location),
                vector_search_port=PostgreSQLVectorSearch(session),
                llm_router=LLMRouter(
                    flash=VertexGeminiFlash(project_id=gcp_project, location=vertex_location),
                    pro=VertexGeminiPro(project_id=gcp_project, location=vertex_location),
                    claude=VertexClaudeSonnet(project_id=gcp_project),
                ),
            )
            advisory = await pipeline.process(
                diff,
                tenant_id=tenant_id,
                risk_level=risk_level,
            )
            incident_ids = [str(advisory.incident_id)] if advisory.incident_id else []
            return (
                advisory.analysis_text,
                advisory.confidence_score,
                incident_ids,
                advisory.llm_model_used,
            )
    finally:
        await session_factory.close()

    # Should not reach here — the async for always yields exactly one session
    return ("", 0.0, [], "none")


def _build_diff(code: str, context: str | None) -> str:
    """Build a pseudo-diff from a code snippet and optional context.

    The RAGPipeline expects a unified-diff-like text for embedding.
    We construct a synthetic diff that preserves the code content.

    Args:
        code: Code snippet.
        context: Optional description or surrounding context.

    Returns:
        Pseudo-diff string suitable for embedding.
    """
    lines = ["diff --git a/snippet.py b/snippet.py", "+++ b/snippet.py"]
    if context:
        lines.append(f"# Context: {context}")
    for line in code.splitlines():
        lines.append(f"+{line}")
    return "\n".join(lines)
