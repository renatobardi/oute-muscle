"""
T170: SynthesisCandidate lifecycle service.

Manages all state transitions for SynthesisCandidate:
  create          pending
  approve         pending  → approved   (also promotes to L1 rule via rule_repo)
  reject          pending  → rejected
  mark_failed     *        → failed     (or archived if failure_count reaches MAX)
  retry           failed   → pending
  auto_archive    pending  → archived   (stale after AUTO_ARCHIVE_DAYS)
"""

from __future__ import annotations

from typing import Optional, Protocol

from packages.core.src.domain.rules.synthesis_candidate import (
    SynthesisCandidate,
    CandidateStatus,
    MAX_FAILURE_COUNT,
    AUTO_ARCHIVE_DAYS,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SynthesisCandidateNotFound(Exception):
    pass


class SynthesisTransitionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Repository Protocols
# ---------------------------------------------------------------------------

class SynthesisCandidateRepo(Protocol):
    async def get(self, candidate_id: str) -> Optional[SynthesisCandidate]: ...
    async def create(self, candidate: SynthesisCandidate) -> SynthesisCandidate: ...
    async def update_status(
        self,
        candidate_id: str,
        status: CandidateStatus,
        failure_reason: Optional[str] = None,
        increment_failure_count: bool = False,
    ) -> None: ...
    async def list_stale_pending(self, older_than_days: int = AUTO_ARCHIVE_DAYS) -> list[SynthesisCandidate]: ...


class RuleRepo(Protocol):
    async def create(self, rule_data: dict) -> object: ...


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SynthesisService:
    def __init__(
        self,
        candidate_repo: SynthesisCandidateRepo,
        rule_repo: RuleRepo,
    ) -> None:
        self._candidates = candidate_repo
        self._rules = rule_repo

    # ------------------------------------------------------------------
    # approve: pending → approved + promote to L1 rule
    # ------------------------------------------------------------------

    async def approve(self, candidate_id: str, approved_by: str) -> str:
        """
        Approve a pending candidate and promote its generated rule to Layer 1.
        Returns the new rule ID.
        """
        candidate = await self._get_or_raise(candidate_id)

        _assert_transition(
            candidate,
            allowed_from={CandidateStatus.PENDING},
            action="approve",
        )

        # Promote to L1 rule
        promoted = await self._rules.create({
            "id": candidate.rule_id,
            "yaml": candidate.generated_rule_yaml,
            "approved_by": approved_by,
            "source": "synthesized",
            "incident_id": None,  # set by caller if available
        })

        await self._candidates.update_status(candidate_id, CandidateStatus.APPROVED)

        rule_id: str = getattr(promoted, "id", candidate.rule_id or "unknown")
        return rule_id

    # ------------------------------------------------------------------
    # reject: pending → rejected
    # ------------------------------------------------------------------

    async def reject(self, candidate_id: str) -> None:
        candidate = await self._get_or_raise(candidate_id)
        _assert_transition(
            candidate,
            allowed_from={CandidateStatus.PENDING},
            action="reject",
        )
        await self._candidates.update_status(candidate_id, CandidateStatus.REJECTED)

    # ------------------------------------------------------------------
    # mark_failed: any → failed (or archived at MAX_FAILURE_COUNT)
    # ------------------------------------------------------------------

    async def mark_failed(self, candidate_id: str, reason: str) -> None:
        candidate = await self._get_or_raise(candidate_id)

        new_failure_count = candidate.failure_count + 1

        if new_failure_count >= MAX_FAILURE_COUNT:
            await self._candidates.update_status(
                candidate_id,
                CandidateStatus.ARCHIVED,
                failure_reason=reason,
                increment_failure_count=True,
            )
        else:
            await self._candidates.update_status(
                candidate_id,
                CandidateStatus.FAILED,
                failure_reason=reason,
                increment_failure_count=True,
            )

    # ------------------------------------------------------------------
    # retry: failed → pending (if not archived)
    # ------------------------------------------------------------------

    async def retry(self, candidate_id: str) -> None:
        candidate = await self._get_or_raise(candidate_id)

        if candidate.status == CandidateStatus.ARCHIVED:
            raise SynthesisTransitionError(
                f"Cannot retry archived candidate {candidate_id}. "
                f"Archived candidates have exceeded the maximum failure count."
            )

        _assert_transition(
            candidate,
            allowed_from={CandidateStatus.FAILED},
            action="retry",
        )
        await self._candidates.update_status(candidate_id, CandidateStatus.PENDING)

    # ------------------------------------------------------------------
    # auto_archive: purge stale pending candidates
    # ------------------------------------------------------------------

    async def auto_archive_stale(self) -> int:
        """
        Archive all pending candidates older than AUTO_ARCHIVE_DAYS.
        Returns the number of archived candidates.
        """
        stale = await self._candidates.list_stale_pending(older_than_days=AUTO_ARCHIVE_DAYS)
        for candidate in stale:
            await self._candidates.update_status(candidate.id, CandidateStatus.ARCHIVED)
        return len(stale)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_raise(self, candidate_id: str) -> SynthesisCandidate:
        candidate = await self._candidates.get(candidate_id)
        if candidate is None:
            raise SynthesisCandidateNotFound(
                f"SynthesisCandidate '{candidate_id}' not found."
            )
        return candidate


def _assert_transition(
    candidate: SynthesisCandidate,
    allowed_from: set[CandidateStatus],
    action: str,
) -> None:
    if candidate.status not in allowed_from:
        raise SynthesisTransitionError(
            f"Cannot {action} a candidate in status '{candidate.status.value}'. "
            f"Allowed statuses: {[s.value for s in allowed_from]}."
        )
