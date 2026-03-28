"""Scan domain entity — represents a single code analysis run."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from ..incidents.enums import RiskLevel, ScanStatus, ScanTriggerSource


class Scan(BaseModel):
    """A code analysis run — may involve Layer 1 (Semgrep), Layer 2 (RAG), or both.

    risk_level is NULL for L1-only scans (no RAG analysis performed).
    risk_score is an integer composite: critical=5pts, high=3pts, medium=2pts, low=1pt.
    Thresholds: low < 5, medium 5-12, high > 12.
    """

    model_config = {"frozen": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID

    trigger_source: ScanTriggerSource
    repository: str | None = Field(default=None, max_length=500)
    pr_number: int | None = Field(default=None, ge=1)
    commit_sha: str | None = Field(default=None, max_length=40)
    diff_lines: int | None = Field(default=None, ge=0)
    diff_truncated: bool = False

    # Layer 2 outputs (NULL for L1-only scans)
    risk_level: RiskLevel | None = None
    risk_score: int | None = Field(default=None, ge=0)
    llm_model_used: str | None = Field(default=None, max_length=50)

    layer1_findings_count: int = Field(default=0, ge=0)
    layer2_advisories_count: int = Field(default=0, ge=0)
    duration_ms: int = Field(ge=0)
    status: ScanStatus
    error_message: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_layer2_consistency(self) -> Scan:
        """risk_level and risk_score must be set together or both absent."""
        has_level = self.risk_level is not None
        has_score = self.risk_score is not None
        if has_level != has_score:
            raise ValueError(
                "risk_level and risk_score must both be set or both be None. "
                f"Got risk_level={self.risk_level}, risk_score={self.risk_score}"
            )
        return self

    @model_validator(mode="after")
    def validate_completed_state(self) -> Scan:
        if self.status == ScanStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed_at must be set when status is COMPLETED.")
        if self.status in (ScanStatus.FAILED, ScanStatus.TIMEOUT) and self.error_message is None:
            raise ValueError(
                f"error_message must be set when status is {self.status}."
            )
        return self

    @property
    def is_l2(self) -> bool:
        """True if this scan included Layer 2 RAG analysis."""
        return self.risk_level is not None
