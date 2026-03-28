"""Finding and Advisory domain entities (Layer 1 and Layer 2 outputs)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from ..incidents.enums import IncidentSeverity, RiskLevel


class Finding(BaseModel):
    """A Layer 1 match — Semgrep rule triggered on a specific file location.

    Constitution VI: code_snippet is context only, never full source code.
    """

    model_config = {"frozen": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    scan_id: uuid.UUID
    tenant_id: uuid.UUID
    rule_id: str = Field(min_length=1, max_length=50)
    incident_id: uuid.UUID

    file_path: str = Field(min_length=1, max_length=1000)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    code_snippet: str | None = None  # context only, not full source — Constitution VI

    severity: IncidentSeverity
    message: str = Field(min_length=1)
    remediation: str = Field(min_length=1)
    false_positive_reported: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("end_line")
    @classmethod
    def end_line_gte_start_line(cls, v: int, info) -> int:  # type: ignore[no-untyped-def]
        """Validate that end_line >= start_line."""
        if "start_line" in info.data and v < info.data["start_line"]:
            raise ValueError(
                f"end_line ({v}) must be >= start_line ({info.data['start_line']})"
            )
        return v


class Advisory(BaseModel):
    """A Layer 2 RAG output — LLM-generated advisory linking diff to past incident.

    file_path and start_line are nullable: NULL means top-level PR comment.
    """

    model_config = {"frozen": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    scan_id: uuid.UUID
    tenant_id: uuid.UUID
    incident_id: uuid.UUID

    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    matched_anti_pattern: str = Field(min_length=1)
    analysis_text: str = Field(min_length=1)
    llm_model_used: str = Field(min_length=1, max_length=50)

    # Nullable: set when advisory can be anchored to a file/line in the diff
    file_path: str | None = Field(default=None, max_length=1000)
    start_line: int | None = Field(default=None, ge=1)
    github_comment_id: int | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_anchored(self) -> bool:
        """True if this advisory can be posted as an inline PR comment."""
        return self.file_path is not None and self.start_line is not None
