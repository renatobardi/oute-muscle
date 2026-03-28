"""
T165: Unit tests for SynthesisCandidate lifecycle.

State machine:
  pending  → approved  → (promoted to L1 rule)
  pending  → rejected
  pending  → failed    → pending (retry with backoff, if failure_count < 3)
  failed   → archived  (if failure_count >= 3)
  pending  → archived  (after 30 days via auto-archive job)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from packages.core.src.domain.rules.synthesis_service import (
    SynthesisService,
    SynthesisCandidateNotFound,
    SynthesisTransitionError,
)
from packages.core.src.domain.rules.synthesis_candidate import (
    SynthesisCandidate,
    CandidateStatus,
    MAX_FAILURE_COUNT,
    AUTO_ARCHIVE_DAYS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candidate(
    status: CandidateStatus = CandidateStatus.PENDING,
    failure_count: int = 0,
    created_at: datetime | None = None,
) -> SynthesisCandidate:
    return SynthesisCandidate(
        id="cand-1",
        anti_pattern_hash="abc123",
        advisory_count=4,
        status=status,
        failure_count=failure_count,
        failure_reason=None,
        generated_rule_yaml=None,
        created_at=created_at or datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestCandidateConstants:
    def test_max_failure_count_is_3(self):
        assert MAX_FAILURE_COUNT == 3

    def test_auto_archive_days_is_30(self):
        assert AUTO_ARCHIVE_DAYS == 30


# ---------------------------------------------------------------------------
# Status: pending → approved → promoted
# ---------------------------------------------------------------------------

class TestApproveTransition:
    @pytest.mark.asyncio
    async def test_approve_pending_candidate(self):
        candidate = make_candidate(CandidateStatus.PENDING)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate
        mock_repo.update_status.return_value = None
        mock_rule_repo = AsyncMock()
        mock_rule_repo.create.return_value = MagicMock(id="cascading-failure-002")

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=mock_rule_repo)
        rule_id = await service.approve("cand-1", approved_by="user-admin")

        mock_repo.update_status.assert_called_once_with(
            "cand-1", CandidateStatus.APPROVED
        )
        assert rule_id is not None

    @pytest.mark.asyncio
    async def test_approve_rejected_candidate_raises(self):
        candidate = make_candidate(CandidateStatus.REJECTED)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())

        with pytest.raises(SynthesisTransitionError) as exc:
            await service.approve("cand-1", approved_by="user-admin")

        assert "rejected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_approve_archived_candidate_raises(self):
        candidate = make_candidate(CandidateStatus.ARCHIVED)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())

        with pytest.raises(SynthesisTransitionError):
            await service.approve("cand-1", approved_by="user-admin")

    @pytest.mark.asyncio
    async def test_approve_nonexistent_candidate_raises(self):
        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())

        with pytest.raises(SynthesisCandidateNotFound):
            await service.approve("does-not-exist", approved_by="user-admin")


# ---------------------------------------------------------------------------
# Status: pending → rejected
# ---------------------------------------------------------------------------

class TestRejectTransition:
    @pytest.mark.asyncio
    async def test_reject_pending_candidate(self):
        candidate = make_candidate(CandidateStatus.PENDING)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        await service.reject("cand-1")

        mock_repo.update_status.assert_called_once_with("cand-1", CandidateStatus.REJECTED)

    @pytest.mark.asyncio
    async def test_reject_already_approved_raises(self):
        candidate = make_candidate(CandidateStatus.APPROVED)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())

        with pytest.raises(SynthesisTransitionError):
            await service.reject("cand-1")


# ---------------------------------------------------------------------------
# Status: pending → failed → retry or archive
# ---------------------------------------------------------------------------

class TestFailedTransition:
    @pytest.mark.asyncio
    async def test_first_failure_transitions_to_failed_and_stays_retriable(self):
        candidate = make_candidate(CandidateStatus.PENDING, failure_count=0)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        await service.mark_failed("cand-1", reason="semgrep --test failed: 2 errors")

        mock_repo.update_status.assert_called_once_with(
            "cand-1",
            CandidateStatus.FAILED,
            failure_reason="semgrep --test failed: 2 errors",
            increment_failure_count=True,
        )

    @pytest.mark.asyncio
    async def test_second_failure_stays_failed_not_archived(self):
        candidate = make_candidate(CandidateStatus.FAILED, failure_count=1)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        await service.mark_failed("cand-1", reason="LLM returned invalid YAML")

        call_kwargs = mock_repo.update_status.call_args
        assert call_kwargs[0][1] == CandidateStatus.FAILED

    @pytest.mark.asyncio
    async def test_third_failure_auto_archives(self):
        """failure_count reaches MAX_FAILURE_COUNT (3) → transition to ARCHIVED."""
        candidate = make_candidate(CandidateStatus.FAILED, failure_count=2)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        await service.mark_failed("cand-1", reason="Repeated LLM failure")

        call_args = mock_repo.update_status.call_args
        assert call_args[0][1] == CandidateStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_retry_resets_status_to_pending(self):
        candidate = make_candidate(CandidateStatus.FAILED, failure_count=1)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        await service.retry("cand-1")

        mock_repo.update_status.assert_called_once_with("cand-1", CandidateStatus.PENDING)

    @pytest.mark.asyncio
    async def test_retry_archived_candidate_raises(self):
        candidate = make_candidate(CandidateStatus.ARCHIVED, failure_count=3)
        mock_repo = AsyncMock()
        mock_repo.get.return_value = candidate

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())

        with pytest.raises(SynthesisTransitionError) as exc:
            await service.retry("cand-1")

        assert "archived" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Auto-archive stale pending candidates
# ---------------------------------------------------------------------------

class TestAutoArchive:
    @pytest.mark.asyncio
    async def test_auto_archive_pending_older_than_30_days(self):
        old_candidate = make_candidate(
            CandidateStatus.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(days=31),
        )
        mock_repo = AsyncMock()
        mock_repo.list_stale_pending.return_value = [old_candidate]

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        archived_count = await service.auto_archive_stale()

        assert archived_count == 1
        mock_repo.update_status.assert_called_once_with(
            old_candidate.id, CandidateStatus.ARCHIVED
        )

    @pytest.mark.asyncio
    async def test_does_not_archive_pending_within_30_days(self):
        recent_candidate = make_candidate(
            CandidateStatus.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        mock_repo = AsyncMock()
        mock_repo.list_stale_pending.return_value = []

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        archived_count = await service.auto_archive_stale()

        assert archived_count == 0
        mock_repo.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_archive_returns_total_archived_count(self):
        stale_candidates = [
            make_candidate(CandidateStatus.PENDING, created_at=datetime.now(timezone.utc) - timedelta(days=35)),
            make_candidate(CandidateStatus.PENDING, created_at=datetime.now(timezone.utc) - timedelta(days=40)),
        ]
        stale_candidates[1].id = "cand-2"

        mock_repo = AsyncMock()
        mock_repo.list_stale_pending.return_value = stale_candidates

        service = SynthesisService(candidate_repo=mock_repo, rule_repo=AsyncMock())
        archived_count = await service.auto_archive_stale()

        assert archived_count == 2
        assert mock_repo.update_status.call_count == 2
