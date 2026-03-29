"""
T167: Pattern detection service.

Detects anti-patterns that have been flagged by the RAG advisory (L2) enough
times to warrant automatic Semgrep rule synthesis (L3).

Trigger condition: 3+ advisories share the same anti_pattern_hash AND no
non-retriable candidate already exists for that hash.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Protocol

SYNTHESIS_THRESHOLD: int = 3  # must stay in sync with synthesis_candidate.py


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PatternMatch:
    """A hash that has reached (or exceeded) the synthesis threshold."""

    hash: str
    count: int
    sample_incident_id: str


# ---------------------------------------------------------------------------
# Repository Protocol (injected, implemented by DB adapter)
# ---------------------------------------------------------------------------


class PatternDetectorRepo(Protocol):
    async def count_advisories_by_hash(self) -> list[PatternMatch]:
        """Return (hash, count, sample_incident_id) for all hashes with count >= threshold."""
        ...

    async def existing_candidate_hashes(self) -> set[str]:
        """Return hashes that already have a pending, approved, or archived candidate."""
        ...

    async def retriable_failed_hashes(self) -> set[str]:
        """Return hashes whose only candidate is in 'failed' status with failure_count < MAX."""
        ...


# ---------------------------------------------------------------------------
# PatternDetector service
# ---------------------------------------------------------------------------


class PatternDetector:
    """Stateless detection service. All state comes from the injected repo."""

    def should_trigger(self, advisories: list[dict[str, Any]]) -> bool:
        """Return True if the given list of same-hash advisories meets the threshold."""
        return len(advisories) >= SYNTHESIS_THRESHOLD

    def group_by_hash(self, advisories: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group a flat list of advisory dicts by their anti_pattern_hash."""
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for advisory in advisories:
            groups[advisory["anti_pattern_hash"]].append(advisory)
        return dict(groups)

    async def detect_triggerable(self, repo: PatternDetectorRepo) -> list[PatternMatch]:
        """
        Query the repo for pattern hashes that:
          1. Have advisory_count >= SYNTHESIS_THRESHOLD
          2. Do NOT already have a blocking candidate (pending/approved/archived),
             UNLESS the existing candidate is in a retriable failed state.

        Returns a list of PatternMatch objects ready for synthesis.
        """
        candidates_above_threshold = await repo.count_advisories_by_hash()
        blocked_hashes = await repo.existing_candidate_hashes()
        retriable_hashes = await repo.retriable_failed_hashes()

        triggerable: list[PatternMatch] = []

        for match in candidates_above_threshold:
            if match.count < SYNTHESIS_THRESHOLD:
                continue

            is_blocked = match.hash in blocked_hashes
            is_retriable = match.hash in retriable_hashes

            # Blocked hashes that are NOT in the retriable set are skipped
            if is_blocked and not is_retriable:
                continue

            triggerable.append(match)

        return triggerable
