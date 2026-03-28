"""
Domain value objects for synthesis candidates.
Shared between pattern_detector, synthesizer, synthesis_service, and worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FAILURE_COUNT: int = 3
AUTO_ARCHIVE_DAYS: int = 30
SYNTHESIS_THRESHOLD: int = 3  # also mirrored in pattern_detector


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CandidateStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Domain entity
# ---------------------------------------------------------------------------


@dataclass
class SynthesisCandidate:
    id: str
    anti_pattern_hash: str
    advisory_count: int
    status: CandidateStatus
    failure_count: int
    failure_reason: str | None
    generated_rule_yaml: str | None
    created_at: datetime
    updated_at: datetime

    # Populated after synthesis
    rule_id: str | None = field(default=None)
    test_file: str | None = field(default=None)

    @property
    def is_retriable(self) -> bool:
        return self.status == CandidateStatus.FAILED and self.failure_count < MAX_FAILURE_COUNT

    @property
    def should_archive_on_next_failure(self) -> bool:
        return self.failure_count >= MAX_FAILURE_COUNT - 1

    @property
    def is_stale(self) -> bool:
        """True if pending for more than AUTO_ARCHIVE_DAYS days."""
        if self.status != CandidateStatus.PENDING:
            return False
        age = (
            datetime.now(UTC)
            - self.created_at.replace(tzinfo=UTC if self.created_at.tzinfo is None else None)
            if self.created_at.tzinfo is None
            else datetime.now(UTC) - self.created_at
        )
        return age.days >= AUTO_ARCHIVE_DAYS
