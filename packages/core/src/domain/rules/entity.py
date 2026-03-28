"""SemgrepRule domain entity."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ..incidents.enums import (
    IncidentCategory,
    IncidentSeverity,
    RuleSource,
    RuleSeverity,
)

RULE_ID_PATTERN = re.compile(
    r"^(unsafe-regex|race-condition|missing-error-handling|injection|"
    r"resource-exhaustion|missing-safety-check|deployment-error|"
    r"data-consistency|unsafe-api-usage|cascading-failure)-\d{3}$"
)


class SemgrepRule(BaseModel):
    """A Semgrep detection rule linked to a production incident.

    Constitution II: Every rule must link to a real incident.
    ID format: {category}-{NNN} e.g. 'unsafe-regex-001'
    """

    model_config = {"frozen": True}

    id: str = Field(min_length=1, max_length=50)  # e.g. 'unsafe-regex-001'
    tenant_id: Optional[uuid.UUID] = None  # NULL = public rule

    incident_id: uuid.UUID
    category: IncidentCategory
    sequence_number: int = Field(ge=1)
    revision: int = Field(default=1, ge=1)

    yaml_content: str = Field(min_length=1)
    test_file_content: str = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    severity: RuleSeverity
    message: str = Field(min_length=1)
    remediation: str = Field(min_length=1)

    source: RuleSource
    synthesis_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    enabled: bool = True
    false_positive_count: int = Field(default=0, ge=0)
    auto_disabled: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not RULE_ID_PATTERN.match(v):
            raise ValueError(
                f"Rule ID must match pattern '{{category}}-{{NNN}}', got '{v}'. "
                f"Valid categories: unsafe-regex, race-condition, missing-error-handling, "
                f"injection, resource-exhaustion, missing-safety-check, deployment-error, "
                f"data-consistency, unsafe-api-usage, cascading-failure"
            )
        return v

    @model_validator(mode="after")
    def validate_synthesis_approval(self) -> "SemgrepRule":
        """Synthesized rules require explicit approval; manual rules are auto-approved."""
        if self.source == RuleSource.SYNTHESIZED and self.synthesis_confidence is None:
            raise ValueError("Synthesized rules must have a synthesis_confidence score.")
        return self

    @model_validator(mode="after")
    def validate_auto_disable_threshold(self) -> "SemgrepRule":
        if self.false_positive_count >= 3 and not self.auto_disabled:
            raise ValueError(
                "Rule with false_positive_count >= 3 must have auto_disabled=True."
            )
        return self

    @property
    def is_approved(self) -> bool:
        return self.approved_by is not None and self.approved_at is not None
