"""Shared test fixtures for packages/core.

Constitution VII: All integration tests must use real implementations,
not mocks, for: incident ingestion, pgvector search, rule generation via LLM.
Unit tests may use mocks for ports only.
"""

import uuid
from datetime import datetime

import pytest

from packages.core.src.domain.incidents.entity import Incident
from packages.core.src.domain.incidents.enums import (
    IncidentCategory,
    IncidentSeverity,
    RuleSeverity,
    RuleSource,
    ScanStatus,
    ScanTriggerSource,
)
from packages.core.src.domain.rules.entity import SemgrepRule
from packages.core.src.domain.scanning.entities import Finding
from packages.core.src.domain.scanning.scan import Scan


@pytest.fixture
def tenant_id() -> uuid.UUID:
    """A fixed tenant UUID for use in tests requiring tenant context."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def user_id() -> uuid.UUID:
    """A fixed user UUID for use in tests."""
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def incident_id() -> uuid.UUID:
    """A fixed incident UUID for use in tests."""
    return uuid.UUID("00000000-0000-0000-0000-000000000003")


@pytest.fixture
def sample_incident(tenant_id: uuid.UUID, user_id: uuid.UUID, incident_id: uuid.UUID) -> Incident:
    """A minimal valid Incident for unit tests."""
    return Incident(
        id=incident_id,
        tenant_id=tenant_id,
        title="Catastrophic backtracking in email validation regex",
        category=IncidentCategory.UNSAFE_REGEX,
        severity=IncidentSeverity.CRITICAL,
        anti_pattern="Using (a+)+ or similar nested quantifiers in regex",
        remediation="Use atomic groups or possessive quantifiers; add timeout",
        created_by=user_id,
    )


@pytest.fixture
def sample_incident_with_embedding(sample_incident: Incident) -> Incident:
    """Incident with a valid 768-dimensional embedding."""
    return sample_incident.with_embedding([0.1] * 768)


@pytest.fixture
def sample_rule(incident_id: uuid.UUID) -> SemgrepRule:
    """A minimal valid SemgrepRule for unit tests."""
    return SemgrepRule(
        id="unsafe-regex-001",
        incident_id=incident_id,
        category=IncidentCategory.UNSAFE_REGEX,
        sequence_number=1,
        yaml_content=(
            "rules:\n"
            "  - id: unsafe-regex-001\n"
            "    message: Catastrophic backtracking risk\n"
            "    severity: ERROR\n"
            "    languages: [python]\n"
            "    pattern: re.compile($REGEX)\n"
        ),
        test_file_content="# ok: safe_regex = re.compile(r'^[a-z]+$')\n",
        languages=["python"],
        severity=RuleSeverity.ERROR,
        message="Potentially catastrophic backtracking regex detected",
        remediation="Use atomic groups or possessive quantifiers",
        source=RuleSource.MANUAL,
    )


@pytest.fixture
def sample_scan(tenant_id: uuid.UUID) -> Scan:
    """A minimal completed L1-only scan for unit tests."""
    return Scan(
        tenant_id=tenant_id,
        trigger_source=ScanTriggerSource.GITHUB_PR,
        repository="org/repo",
        pr_number=42,
        commit_sha="abc123def456" + "0" * 28,
        diff_lines=150,
        layer1_findings_count=1,
        duration_ms=450,
        status=ScanStatus.COMPLETED,
        completed_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_finding(tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Finding:
    """A minimal Finding for unit tests."""
    scan_id = uuid.uuid4()
    return Finding(
        scan_id=scan_id,
        tenant_id=tenant_id,
        rule_id="unsafe-regex-001",
        incident_id=incident_id,
        file_path="src/validators/email.py",
        start_line=42,
        end_line=42,
        severity=IncidentSeverity.CRITICAL,
        message="Catastrophic backtracking risk in regex",
        remediation="Use atomic groups or possessive quantifiers",
    )
