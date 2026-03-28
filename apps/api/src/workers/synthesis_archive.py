"""
T173: Auto-archive scheduled job.

Archives synthesis candidates that have been in PENDING status for more than
AUTO_ARCHIVE_DAYS days (currently 30).

Invocation:
  - Cloud Scheduler → Cloud Run Job (HTTP POST /jobs/synthesis-archive)
  - Direct CLI:  python -m apps.api.src.workers.synthesis_archive

The job is intentionally idempotent: running it multiple times has no additional
effect after the first pass.

Returns a JSON summary:
  {
    "archived": <int>,  # candidates archived in this run
    "run_at":   "<ISO timestamp>"
  }
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

import structlog

from packages.core.src.domain.rules.synthesis_service import SynthesisService
from packages.core.src.domain.rules.synthesis_candidate import (
    CandidateStatus,
    AUTO_ARCHIVE_DAYS,
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Repository port
# ---------------------------------------------------------------------------

class ArchiveCandidateRepo(Protocol):
    async def get(self, candidate_id: str) -> Optional[Any]: ...
    async def create(self, candidate: Any) -> Any: ...
    async def update_status(
        self,
        candidate_id: str,
        status: CandidateStatus,
        failure_reason: Optional[str] = None,
        increment_failure_count: bool = False,
    ) -> None: ...
    async def list_stale_pending(self, older_than_days: int) -> list[Any]: ...


class ArchiveRuleRepo(Protocol):
    async def create(self, rule_data: dict) -> object: ...


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

async def run_archive_job(
    candidate_repo: ArchiveCandidateRepo,
    rule_repo: ArchiveRuleRepo,
) -> dict:
    """
    Archive all stale pending candidates.
    Returns a summary dict with the count of archived candidates and the run timestamp.
    """
    service = SynthesisService(
        candidate_repo=candidate_repo,
        rule_repo=rule_repo,
    )

    run_at = datetime.now(timezone.utc)

    log.info("synthesis_archive_job_start", auto_archive_days=AUTO_ARCHIVE_DAYS)

    archived_count = await service.auto_archive_stale()

    log.info(
        "synthesis_archive_job_complete",
        archived=archived_count,
        run_at=run_at.isoformat(),
    )

    return {
        "archived": archived_count,
        "run_at": run_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# FastAPI route (mounted by the app factory)
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

archive_router = APIRouter(prefix="/jobs", tags=["jobs"])


class ArchiveJobResponse(BaseModel):
    archived: int
    run_at: str


@archive_router.post(
    "/synthesis-archive",
    response_model=ArchiveJobResponse,
    summary="Archive stale synthesis candidates (Cloud Scheduler job)",
)
async def synthesis_archive_job(request: Request) -> ArchiveJobResponse:
    """
    Triggered by Cloud Scheduler. Archives pending candidates older than
    AUTO_ARCHIVE_DAYS days.

    Protected by Cloud IAM (service account invocation) — no user auth required.
    """
    candidate_repo = getattr(request.app.state, "candidate_repo", None)
    rule_repo = getattr(request.app.state, "rule_repo", None)

    if candidate_repo is None or rule_repo is None:
        raise HTTPException(status_code=500, detail="Repositories not configured")

    result = await run_archive_job(
        candidate_repo=candidate_repo,
        rule_repo=rule_repo,
    )
    return ArchiveJobResponse(**result)


# ---------------------------------------------------------------------------
# CLI entry point (Cloud Run Job)
# ---------------------------------------------------------------------------

async def _cli_main() -> None:
    """
    Standalone runner for Cloud Run Job execution.

    Expects DATABASE_URL and other env vars to be set.
    Imports are deferred so this module can be imported in unit tests without
    triggering DB setup.
    """
    import os

    # Deferred DB setup
    from packages.db.src.session import get_async_session_factory  # type: ignore[import]
    from apps.api.src.adapters.db.synthesis_repo import SQLSynthesisCandidateRepo  # type: ignore[import]
    from apps.api.src.adapters.db.rule_repo import SQLRuleRepo  # type: ignore[import]

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    session_factory = get_async_session_factory(database_url)

    async with session_factory() as session:
        candidate_repo = SQLSynthesisCandidateRepo(session)
        rule_repo = SQLRuleRepo(session)
        result = await run_archive_job(candidate_repo, rule_repo)

    print(result)


if __name__ == "__main__":
    asyncio.run(_cli_main())
