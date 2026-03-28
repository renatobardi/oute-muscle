"""
T171: Synthesis worker.

Entry points:
  - handle_cloud_tasks_request(payload)  — called by the Cloud Tasks HTTP handler
  - process_candidate(candidate_id)      — core pipeline (also callable in tests)

Pipeline per candidate:
  1. Load candidate from DB (must be PENDING)
  2. Load source incident from DB
  3. Call RuleSynthesizer → SynthesisResult
  4. Run CandidateTestValidator (semgrep --test)
  5a. Tests pass  → SynthesisService.approve()
  5b. Tests fail  → SynthesisService.mark_failed()

Retry schedule (Cloud Tasks):
  attempt 1 → immediate
  attempt 2 → 1 min backoff
  attempt 3 → 5 min backoff
  ≥ attempt 4 → 15 min backoff  (also final — MAX_FAILURE_COUNT reached, archived)

The Cloud Tasks queue controls the actual delay; this module reports the *requested*
retry delay via the X-CloudTasks-RetryDelay response header so the queue adapter
can schedule accordingly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol

import structlog

from packages.core.src.domain.rules.pattern_detector import PatternDetector, PatternDetectorRepo
from packages.core.src.domain.rules.synthesizer import RuleSynthesizer, SynthesisError
from packages.core.src.domain.rules.test_validator import CandidateTestValidator
from packages.core.src.domain.rules.synthesis_service import (
    SynthesisService,
    SynthesisCandidateNotFound,
    SynthesisTransitionError,
)
from packages.core.src.domain.rules.synthesis_candidate import (
    SynthesisCandidate,
    CandidateStatus,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Retry schedule
# ---------------------------------------------------------------------------

RETRY_DELAYS_SECONDS: list[int] = [
    0,      # attempt 1 — immediate
    60,     # attempt 2 — 1 min
    300,    # attempt 3 — 5 min
    900,    # attempt 4+ — 15 min
]


def retry_delay_for_attempt(attempt: int) -> int:
    """Return the requested retry delay in seconds for the given attempt number (1-based)."""
    if attempt <= 0:
        return 0
    idx = min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)
    return RETRY_DELAYS_SECONDS[idx]


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class WorkerPayload:
    """Payload delivered by Cloud Tasks HTTP request body."""
    candidate_id: str
    attempt: int = 1  # Cloud Tasks X-CloudTasks-TaskRetryCount + 1


@dataclass
class WorkerResult:
    """Result returned to the Cloud Tasks handler."""
    success: bool
    candidate_id: str
    rule_id: Optional[str] = None
    failure_reason: Optional[str] = None
    # When success=False and retry is possible, set this to signal the caller
    # to re-enqueue with the appropriate delay.
    retry_delay_seconds: Optional[int] = None
    archived: bool = False


# ---------------------------------------------------------------------------
# Repository and service ports
# ---------------------------------------------------------------------------

class IncidentRepo(Protocol):
    async def get(self, incident_id: str) -> Optional[dict]: ...


class CandidateWriteRepo(Protocol):
    async def get(self, candidate_id: str) -> Optional[SynthesisCandidate]: ...
    async def create(self, candidate: SynthesisCandidate) -> SynthesisCandidate: ...
    async def update_status(
        self,
        candidate_id: str,
        status: CandidateStatus,
        failure_reason: Optional[str] = None,
        increment_failure_count: bool = False,
    ) -> None: ...
    async def list_stale_pending(self, older_than_days: int) -> list[SynthesisCandidate]: ...


class RuleWriteRepo(Protocol):
    async def create(self, rule_data: dict) -> object: ...


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class SynthesisWorker:
    """
    Orchestrates the synthesis pipeline for a single candidate.
    All dependencies are injected for testability.
    """

    def __init__(
        self,
        candidate_repo: CandidateWriteRepo,
        rule_repo: RuleWriteRepo,
        incident_repo: IncidentRepo,
        synthesizer: RuleSynthesizer,
        validator: CandidateTestValidator,
    ) -> None:
        self._candidate_repo = candidate_repo
        self._rule_repo = rule_repo
        self._incident_repo = incident_repo
        self._synthesizer = synthesizer
        self._validator = validator
        self._service = SynthesisService(
            candidate_repo=candidate_repo,
            rule_repo=rule_repo,
        )

    async def process(self, payload: WorkerPayload) -> WorkerResult:
        """
        Run the full synthesis pipeline for the given candidate.
        Never raises — all failures are encoded in WorkerResult.
        """
        candidate_id = payload.candidate_id
        attempt = payload.attempt

        bound_log = log.bind(candidate_id=candidate_id, attempt=attempt)

        # ── 1. Load candidate ───────────────────────────────────────────────
        try:
            candidate = await self._candidate_repo.get(candidate_id)
        except Exception as exc:
            bound_log.error("db_error_loading_candidate", error=str(exc))
            return WorkerResult(
                success=False,
                candidate_id=candidate_id,
                failure_reason=f"DB error loading candidate: {exc}",
                retry_delay_seconds=retry_delay_for_attempt(attempt + 1),
            )

        if candidate is None:
            bound_log.warning("candidate_not_found")
            return WorkerResult(
                success=False,
                candidate_id=candidate_id,
                failure_reason="Candidate not found",
            )

        if candidate.status != CandidateStatus.PENDING:
            bound_log.info("candidate_not_pending", status=candidate.status.value)
            return WorkerResult(
                success=False,
                candidate_id=candidate_id,
                failure_reason=f"Candidate is not pending (status={candidate.status.value})",
            )

        # ── 2. Load source incident ─────────────────────────────────────────
        incident = await self._load_incident(candidate, bound_log)
        if incident is None:
            reason = f"Incident not found for candidate {candidate_id}"
            await self._fail(candidate_id, reason, attempt, bound_log)
            return self._failed_result(candidate_id, reason, attempt, candidate)

        # ── 3. Synthesize rule ──────────────────────────────────────────────
        try:
            synthesis_result = await self._synthesizer.synthesize(incident)
            bound_log.info("synthesis_complete", rule_id=synthesis_result.rule_id)
        except SynthesisError as exc:
            reason = f"Synthesis failed: {exc}"
            bound_log.warning("synthesis_error", error=str(exc))
            await self._fail(candidate_id, reason, attempt, bound_log)
            return self._failed_result(candidate_id, reason, attempt, candidate)
        except Exception as exc:
            reason = f"Unexpected synthesis error: {exc}"
            bound_log.error("synthesis_unexpected_error", error=str(exc))
            await self._fail(candidate_id, reason, attempt, bound_log)
            return self._failed_result(candidate_id, reason, attempt, candidate)

        # ── 4. Validate generated rule with semgrep --test ──────────────────
        validation = await self._validator.validate(synthesis_result)

        if not validation.passed:
            reason = "semgrep --test failed: " + "; ".join(validation.errors[:5])
            bound_log.warning("validation_failed", errors=validation.errors[:5])
            await self._fail(candidate_id, reason, attempt, bound_log)
            return self._failed_result(candidate_id, reason, attempt, candidate)

        bound_log.info("validation_passed")

        # ── 5. Approve and promote to L1 ────────────────────────────────────
        try:
            rule_id = await self._service.approve(
                candidate_id=candidate_id,
                approved_by="synthesis-worker",
            )
            bound_log.info("candidate_approved", rule_id=rule_id)
            return WorkerResult(
                success=True,
                candidate_id=candidate_id,
                rule_id=rule_id,
            )
        except SynthesisTransitionError as exc:
            # Already approved/rejected by a human while we were processing
            bound_log.warning("approval_transition_error", error=str(exc))
            return WorkerResult(
                success=False,
                candidate_id=candidate_id,
                failure_reason=str(exc),
            )
        except Exception as exc:
            reason = f"Approval failed: {exc}"
            bound_log.error("approval_error", error=str(exc))
            return WorkerResult(
                success=False,
                candidate_id=candidate_id,
                failure_reason=reason,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_incident(
        self,
        candidate: SynthesisCandidate,
        bound_log: structlog.BoundLogger,
    ) -> Optional[dict]:
        """Load the incident that seeded this candidate (via sample_incident_id if stored)."""
        # Candidates created by the trigger worker carry the incident reference
        # in their anti_pattern_hash; however the simplest approach is to look up
        # the first advisory that matches the hash and load its incident.
        # For now we delegate to the incident_repo with the hash as a fallback key.
        try:
            # Try direct ID lookup first (populated when candidate is created)
            incident_id = getattr(candidate, "incident_id", None)
            if incident_id:
                return await self._incident_repo.get(incident_id)
            # Fallback: use anti_pattern_hash as a surrogate (repo may resolve this)
            return await self._incident_repo.get(candidate.anti_pattern_hash)
        except Exception as exc:
            bound_log.error("db_error_loading_incident", error=str(exc))
            return None

    async def _fail(
        self,
        candidate_id: str,
        reason: str,
        attempt: int,
        bound_log: structlog.BoundLogger,
    ) -> None:
        """Persist failure to the candidate. Swallows DB errors to keep the pipeline clean."""
        try:
            await self._service.mark_failed(candidate_id, reason)
        except Exception as exc:
            bound_log.error("failed_to_persist_failure", error=str(exc))

    def _failed_result(
        self,
        candidate_id: str,
        reason: str,
        attempt: int,
        candidate: SynthesisCandidate,
    ) -> WorkerResult:
        """Build a WorkerResult for a failed attempt, computing retry delay if applicable."""
        new_failure_count = candidate.failure_count + 1
        from packages.core.src.domain.rules.synthesis_candidate import MAX_FAILURE_COUNT
        archived = new_failure_count >= MAX_FAILURE_COUNT
        retry_delay = None if archived else retry_delay_for_attempt(attempt + 1)
        return WorkerResult(
            success=False,
            candidate_id=candidate_id,
            failure_reason=reason,
            retry_delay_seconds=retry_delay,
            archived=archived,
        )


# ---------------------------------------------------------------------------
# Cloud Tasks HTTP handler (thin adapter)
# ---------------------------------------------------------------------------

async def handle_cloud_tasks_request(
    payload: WorkerPayload,
    worker: SynthesisWorker,
) -> WorkerResult:
    """
    Adapter called by the FastAPI route that receives Cloud Tasks HTTP deliveries.

    The caller is responsible for:
      - Parsing X-CloudTasks-TaskRetryCount header → payload.attempt
      - Returning 200 on WorkerResult.success=True (Cloud Tasks won't retry)
      - Returning 429/503 on WorkerResult.success=False (Cloud Tasks will retry)
      - Honouring WorkerResult.retry_delay_seconds via the Retry-After header
    """
    return await worker.process(payload)
