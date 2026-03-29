"""RAG Worker — Cloud Run Job for async advisory generation (Phase 5, T097).

Constitution VI: Worker entry point orchestrates RAG pipeline.
Triggered by Cloud Tasks queued from POST /scans with layer=L2|both.

Environment variables (required):
    SCAN_ID        — UUID of the scan to process
    DATABASE_URL   — PostgreSQL connection string (asyncpg)
    GOOGLE_CLOUD_PROJECT — GCP project for Vertex AI
    TENANT_ID      — Tenant UUID for RLS
    DIFF           — Unified diff text (passed by Cloud Tasks at job enqueue time)

Optional:
    VERTEX_LOCATION — GCP region for Vertex AI (default: us-central1)
    LOG_LEVEL       — Logging level (default: INFO)

Flow:
    1. Load scan from PostgreSQL to validate it exists
    2. Load Layer 1 findings → compute risk score
    3. Parse diff from env var
    4. Instantiate Vertex AI adapters and RAGPipeline
    5. Run pipeline: embed → vector search → LLM → Advisory
    6. Persist Advisory to database
    7. Update scan status to 'completed'
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.db.src.adapters.pg_scan_repo import PostgreSQLScanRepo

logger = logging.getLogger(__name__)


async def run_rag_worker() -> int:
    """Main entry point for RAG worker Cloud Run Job.

    Returns:
        Exit code: 0 on success, 1 on failure (triggers Cloud Tasks retry).
    """
    # ── 1. Read required environment variables ─────────────────────────────
    scan_id_str = os.environ.get("SCAN_ID")
    database_url = os.environ.get("DATABASE_URL")
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    tenant_id_str = os.environ.get("TENANT_ID")
    diff = os.environ.get("DIFF", "")
    vertex_location = os.environ.get("VERTEX_LOCATION", "us-central1")

    missing = [
        name
        for name, val in [
            ("SCAN_ID", scan_id_str),
            ("DATABASE_URL", database_url),
            ("GOOGLE_CLOUD_PROJECT", gcp_project),
            ("TENANT_ID", tenant_id_str),
        ]
        if not val
    ]
    if missing:
        logger.error("rag_worker_missing_env_vars", missing=missing)
        return 1

    try:
        scan_id = uuid.UUID(scan_id_str)  # type: ignore[arg-type]
        tenant_id = uuid.UUID(tenant_id_str)  # type: ignore[arg-type]
    except ValueError as exc:
        logger.error("rag_worker_invalid_uuid", error=str(exc))
        return 1

    logger.info(
        "rag_worker_started",
        scan_id=str(scan_id),
        tenant_id=str(tenant_id),
        diff_length=len(diff),
    )
    started_at = time.monotonic()

    # ── 2. Connect to PostgreSQL ────────────────────────────────────────────
    from packages.db.src.session import SessionFactory

    session_factory = SessionFactory(database_url=database_url)  # type: ignore[arg-type]

    try:
        async for session in session_factory.get_session(tenant_id=tenant_id):
            return await _process(
                session=session,
                scan_id=scan_id,
                tenant_id=tenant_id,
                diff=diff,
                gcp_project=gcp_project,  # type: ignore[arg-type]
                vertex_location=vertex_location,
                started_at=started_at,
            )
    except Exception as exc:
        logger.exception("rag_worker_unhandled_error", error=str(exc))
        return 1
    finally:
        await session_factory.close()

    return 0


async def _process(
    *,
    session,
    scan_id: uuid.UUID,
    tenant_id: uuid.UUID,
    diff: str,
    gcp_project: str,
    vertex_location: str,
    started_at: float,
) -> int:
    """Inner processing: load scan, run pipeline, persist results.

    Args:
        session: Active tenant-scoped AsyncSession.
        scan_id: UUID of the scan to process.
        tenant_id: Tenant UUID for RLS scoping.
        diff: Unified diff string (may be empty).
        gcp_project: GCP project ID for Vertex AI.
        vertex_location: GCP region for Vertex AI.
        started_at: monotonic timestamp at worker start (for duration calc).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    from packages.db.src.adapters.pg_advisory_repo import PostgreSQLAdvisoryRepo
    from packages.db.src.adapters.pg_scan_repo import (
        PostgreSQLScanRepo,
        finding_severities,
    )

    scan_repo = PostgreSQLScanRepo(session)
    advisory_repo = PostgreSQLAdvisoryRepo(session)

    # ── 3. Load scan ────────────────────────────────────────────────────────
    scan = await scan_repo.get_by_id(scan_id, tenant_id=tenant_id)
    if scan is None:
        logger.error("rag_worker_scan_not_found", scan_id=str(scan_id))
        return 1

    if scan.status not in ("running", "pending"):
        # Already processed (idempotency guard for Cloud Tasks retries)
        logger.warning(
            "rag_worker_scan_already_processed",
            scan_id=str(scan_id),
            status=scan.status,
        )
        return 0

    # ── 4. Load Layer 1 findings → compute risk score ──────────────────────
    from packages.core.src.domain.scanning.risk_score import (
        compute_risk_score,
        score_to_risk_level,
    )

    findings = await scan_repo.list_findings(scan_id)
    severities = finding_severities(findings)
    risk_score = compute_risk_score(severities)
    risk_level = score_to_risk_level(risk_score)

    logger.info(
        "rag_worker_risk_computed",
        scan_id=str(scan_id),
        findings_count=len(findings),
        risk_score=risk_score,
        risk_level=risk_level.value,
    )

    # ── 5. Guard: skip RAG if diff is empty ────────────────────────────────
    if not diff.strip():
        logger.warning(
            "rag_worker_empty_diff",
            scan_id=str(scan_id),
            note="DIFF env var not set — skipping RAG, marking completed",
        )
        await _mark_completed(scan_repo, scan_id, started_at)
        return 0

    # ── 6. Build Vertex AI adapters ────────────────────────────────────────
    from apps.api.src.adapters.vertex_embedding import VertexAIEmbedding
    from apps.api.src.adapters.vertex_llm import (
        VertexClaudeSonnet,
        VertexGeminiFlash,
        VertexGeminiPro,
    )
    from packages.core.src.domain.advisory.llm_router import LLMRouter

    embedding_adapter = VertexAIEmbedding(project_id=gcp_project, location=vertex_location)
    llm_router = LLMRouter(
        flash=VertexGeminiFlash(project_id=gcp_project, location=vertex_location),
        pro=VertexGeminiPro(project_id=gcp_project, location=vertex_location),
        claude=VertexClaudeSonnet(project_id=gcp_project),
    )

    # ── 7. Build vector search adapter ─────────────────────────────────────
    from packages.db.src.adapters.pg_vector_search import PostgreSQLVectorSearch

    vector_search = PostgreSQLVectorSearch(session)

    # ── 8. Run RAG pipeline ────────────────────────────────────────────────
    from packages.core.src.domain.advisory.rag_pipeline import RAGPipeline

    pipeline = RAGPipeline(
        embedding_port=embedding_adapter,
        vector_search_port=vector_search,
        llm_router=llm_router,
    )

    try:
        advisory = await pipeline.process(
            diff,
            tenant_id=tenant_id,
            risk_level=risk_level,
            scan_id=scan_id,
        )
    except Exception as exc:
        logger.exception(
            "rag_worker_pipeline_error",
            scan_id=str(scan_id),
            error=str(exc),
        )
        await scan_repo.update_status(
            scan_id,
            status="failed",
            completed_at=datetime.now(tz=UTC),
        )
        return 1

    logger.info(
        "rag_worker_advisory_generated",
        scan_id=str(scan_id),
        confidence=advisory.confidence_score,
        risk_level=advisory.risk_level.value,
        model=advisory.llm_model_used,
    )

    # ── 9. Persist Advisory ────────────────────────────────────────────────
    try:
        await advisory_repo.save(advisory)
    except Exception as exc:
        logger.exception(
            "rag_worker_advisory_save_error",
            scan_id=str(scan_id),
            error=str(exc),
        )
        await scan_repo.update_status(
            scan_id,
            status="failed",
            completed_at=datetime.now(tz=UTC),
        )
        return 1

    # ── 10. Mark scan completed ────────────────────────────────────────────
    await _mark_completed(scan_repo, scan_id, started_at)

    logger.info(
        "rag_worker_completed",
        scan_id=str(scan_id),
        duration_ms=int((time.monotonic() - started_at) * 1000),
    )
    return 0


async def _mark_completed(
    scan_repo: PostgreSQLScanRepo,
    scan_id: uuid.UUID,
    started_at: float,
) -> None:
    """Update scan status to 'completed' with timing info.

    Args:
        scan_repo: Scan repository adapter.
        scan_id: The scan to mark completed.
        started_at: Worker start time (monotonic seconds) for duration calc.
    """
    duration_ms = int((time.monotonic() - started_at) * 1000)
    await scan_repo.update_status(
        scan_id,
        status="completed",
        completed_at=datetime.now(tz=UTC),
        duration_ms=duration_ms,
    )


if __name__ == "__main__":
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    exit_code = asyncio.run(run_rag_worker())
    sys.exit(exit_code)
