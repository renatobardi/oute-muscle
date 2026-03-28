"""
T163: Unit tests for pattern detection service.
Invariant: 3+ advisories with the same anti_pattern_hash → trigger synthesis.
"""

import hashlib
from unittest.mock import AsyncMock

import pytest

from packages.core.src.domain.rules.pattern_detector import (
    SYNTHESIS_THRESHOLD,
    PatternDetector,
    PatternMatch,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash(pattern: str) -> str:
    return hashlib.sha256(pattern.encode()).hexdigest()


def make_advisory(anti_pattern: str, incident_id: str = "inc-1") -> dict:
    return {
        "id": f"adv-{anti_pattern[:8]}",
        "incident_id": incident_id,
        "anti_pattern": anti_pattern,
        "anti_pattern_hash": _hash(anti_pattern),
        "confidence": 0.92,
    }


# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------


class TestSynthesisThreshold:
    def test_threshold_is_3(self):
        assert SYNTHESIS_THRESHOLD == 3


# ---------------------------------------------------------------------------
# PatternDetector.should_trigger
# ---------------------------------------------------------------------------


class TestPatternDetectorShouldTrigger:
    def test_returns_false_for_fewer_than_3_matches(self):
        detector = PatternDetector()
        matches = [make_advisory("retry without backoff")] * 2
        assert detector.should_trigger(matches) is False

    def test_returns_true_for_exactly_3_matches(self):
        detector = PatternDetector()
        matches = [make_advisory("retry without backoff")] * 3
        assert detector.should_trigger(matches) is True

    def test_returns_true_for_more_than_3_matches(self):
        detector = PatternDetector()
        matches = [make_advisory("retry without backoff")] * 7
        assert detector.should_trigger(matches) is True

    def test_returns_false_for_empty_list(self):
        detector = PatternDetector()
        assert detector.should_trigger([]) is False


# ---------------------------------------------------------------------------
# PatternDetector.group_by_hash
# ---------------------------------------------------------------------------


class TestPatternDetectorGroupByHash:
    def test_groups_advisories_with_same_hash(self):
        detector = PatternDetector()
        advisories = [
            make_advisory("retry without backoff"),
            make_advisory("retry without backoff"),
            make_advisory("retry without backoff"),
            make_advisory("unbounded goroutine"),
        ]
        groups = detector.group_by_hash(advisories)

        retry_hash = _hash("retry without backoff")
        goroutine_hash = _hash("unbounded goroutine")

        assert len(groups[retry_hash]) == 3
        assert len(groups[goroutine_hash]) == 1

    def test_returns_empty_dict_for_no_advisories(self):
        detector = PatternDetector()
        assert detector.group_by_hash([]) == {}

    def test_each_group_preserves_advisory_order(self):
        detector = PatternDetector()
        a1 = make_advisory("raw sql", "inc-1")
        a2 = make_advisory("raw sql", "inc-2")
        a3 = make_advisory("raw sql", "inc-3")
        groups = detector.group_by_hash([a1, a2, a3])
        h = _hash("raw sql")
        assert groups[h][0]["incident_id"] == "inc-1"
        assert groups[h][2]["incident_id"] == "inc-3"


# ---------------------------------------------------------------------------
# PatternDetector.detect_triggerable (async, queries DB)
# ---------------------------------------------------------------------------


class TestPatternDetectorDetectTriggerable:
    @pytest.mark.asyncio
    async def test_returns_pattern_matches_above_threshold(self):
        detector = PatternDetector()

        mock_repo = AsyncMock()
        retry_hash = _hash("retry without backoff")
        sql_hash = _hash("raw sql")

        # Simulate DB returning advisory counts per hash
        mock_repo.count_advisories_by_hash.return_value = [
            PatternMatch(hash=retry_hash, count=5, sample_incident_id="inc-1"),
            PatternMatch(hash=sql_hash, count=2, sample_incident_id="inc-2"),  # below threshold
        ]

        results = await detector.detect_triggerable(mock_repo)

        assert len(results) == 1
        assert results[0].hash == retry_hash
        assert results[0].count == 5

    @pytest.mark.asyncio
    async def test_excludes_hashes_that_already_have_candidates(self):
        detector = PatternDetector()

        mock_repo = AsyncMock()
        retry_hash = _hash("retry without backoff")

        mock_repo.count_advisories_by_hash.return_value = [
            PatternMatch(hash=retry_hash, count=4, sample_incident_id="inc-1"),
        ]
        # Mark the hash as already having a pending/approved candidate
        mock_repo.existing_candidate_hashes.return_value = {retry_hash}

        results = await detector.detect_triggerable(mock_repo)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_includes_failed_candidates_eligible_for_retry(self):
        """Hashes with 'failed' candidates (below failure_count cap) may be retried."""
        detector = PatternDetector()

        mock_repo = AsyncMock()
        retry_hash = _hash("retry without backoff")

        mock_repo.count_advisories_by_hash.return_value = [
            PatternMatch(hash=retry_hash, count=4, sample_incident_id="inc-1"),
        ]
        # Hash has a failed candidate with failure_count=1 (below cap of 3)
        mock_repo.existing_candidate_hashes.return_value = set()
        mock_repo.retriable_failed_hashes.return_value = {retry_hash}

        results = await detector.detect_triggerable(mock_repo)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_excludes_archived_hashes(self):
        detector = PatternDetector()

        mock_repo = AsyncMock()
        h = _hash("old pattern")

        mock_repo.count_advisories_by_hash.return_value = [
            PatternMatch(hash=h, count=10, sample_incident_id="inc-x"),
        ]
        mock_repo.existing_candidate_hashes.return_value = {h}  # archived
        mock_repo.retriable_failed_hashes.return_value = set()

        results = await detector.detect_triggerable(mock_repo)

        assert len(results) == 0
