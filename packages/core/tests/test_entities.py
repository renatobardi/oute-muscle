"""Unit tests for domain entity validation — required fields, ID format, invariants.

Constitution VII: TDD — test entity constraints.
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
)
from packages.core.src.domain.rules.entity import SemgrepRule


def make_incident(**overrides: object) -> Incident:
    """Factory for valid Incident instances."""
    defaults: dict[str, object] = {
        "title": "Database connection pool exhausted under load",
        "category": IncidentCategory.RESOURCE_EXHAUSTION,
        "severity": IncidentSeverity.HIGH,
        "anti_pattern": "Opening DB connections without pooling",
        "remediation": "Use connection pooling with max_connections limit",
        "created_by": uuid.uuid4(),
    }
    return Incident(**{**defaults, **overrides})


def make_rule(**overrides: object) -> SemgrepRule:
    """Factory for valid SemgrepRule instances."""
    defaults: dict[str, object] = {
        "id": "unsafe-regex-001",
        "incident_id": uuid.uuid4(),
        "category": IncidentCategory.UNSAFE_REGEX,
        "sequence_number": 1,
        "yaml_content": "rules:\n  - id: unsafe-regex-001\n    pattern: ...",
        "test_file_content": "# Test file",
        "languages": ["python"],
        "severity": RuleSeverity.ERROR,
        "message": "Potentially catastrophic regex detected",
        "remediation": "Use regex with atomic groups or possessive quantifiers",
        "source": RuleSource.MANUAL,
    }
    return SemgrepRule(**{**defaults, **overrides})


class TestIncidentRequiredFields:
    def test_valid_incident_creates_successfully(self) -> None:
        incident = make_incident()
        assert incident.title == "Database connection pool exhausted under load"

    def test_title_cannot_be_empty(self) -> None:
        with pytest.raises(Exception):
            make_incident(title="")

    def test_anti_pattern_cannot_be_empty(self) -> None:
        with pytest.raises(Exception):
            make_incident(anti_pattern="")

    def test_remediation_cannot_be_empty(self) -> None:
        with pytest.raises(Exception):
            make_incident(remediation="")

    def test_id_is_uuid(self) -> None:
        incident = make_incident()
        assert isinstance(incident.id, uuid.UUID)

    def test_tenant_id_defaults_to_none(self) -> None:
        incident = make_incident()
        assert incident.tenant_id is None

    def test_version_defaults_to_1(self) -> None:
        incident = make_incident()
        assert incident.version == 1


class TestIncidentEmbeddingValidation:
    def test_valid_768_dimension_embedding_accepted(self) -> None:
        embedding = [0.1] * 768
        incident = make_incident(embedding=embedding)
        assert incident.embedding == embedding

    def test_wrong_dimension_embedding_rejected(self) -> None:
        with pytest.raises(Exception, match="768"):
            make_incident(embedding=[0.1] * 100)

    def test_none_embedding_accepted(self) -> None:
        incident = make_incident(embedding=None)
        assert incident.embedding is None

    def test_with_embedding_returns_new_instance(self) -> None:
        incident = make_incident()
        embedding = [0.5] * 768
        updated = incident.with_embedding(embedding)
        assert updated.embedding == embedding
        assert incident.embedding is None  # original unchanged (frozen)


class TestIncidentRuleIdFormat:
    def test_valid_rule_id_accepted(self) -> None:
        incident = make_incident(semgrep_rule_id="unsafe-regex-001")
        assert incident.semgrep_rule_id == "unsafe-regex-001"

    def test_invalid_rule_id_rejected(self) -> None:
        with pytest.raises(Exception):
            make_incident(semgrep_rule_id="bad-format")

    def test_none_rule_id_accepted(self) -> None:
        incident = make_incident(semgrep_rule_id=None)
        assert incident.semgrep_rule_id is None


class TestIncidentDeletionInvariant:
    def test_cannot_soft_delete_incident_with_active_rule(self) -> None:
        with pytest.raises(Exception, match="semgrep_rule_id"):
            make_incident(
                semgrep_rule_id="unsafe-regex-001",
                deleted_at=datetime.utcnow(),
            )

    def test_can_soft_delete_without_rule(self) -> None:
        incident = make_incident(deleted_at=datetime.utcnow())
        assert incident.is_deleted is True


class TestSemgrepRuleIdFormat:
    def test_valid_id_format_accepted(self) -> None:
        rule = make_rule(id="unsafe-regex-001")
        assert rule.id == "unsafe-regex-001"

    def test_all_valid_categories_accepted(self) -> None:
        categories_map = {
            "unsafe-regex-001": IncidentCategory.UNSAFE_REGEX,
            "race-condition-001": IncidentCategory.RACE_CONDITION,
            "missing-error-handling-001": IncidentCategory.MISSING_ERROR_HANDLING,
            "injection-001": IncidentCategory.INJECTION,
            "resource-exhaustion-001": IncidentCategory.RESOURCE_EXHAUSTION,
            "missing-safety-check-001": IncidentCategory.MISSING_SAFETY_CHECK,
            "deployment-error-001": IncidentCategory.DEPLOYMENT_ERROR,
            "data-consistency-001": IncidentCategory.DATA_CONSISTENCY,
            "unsafe-api-usage-001": IncidentCategory.UNSAFE_API_USAGE,
            "cascading-failure-001": IncidentCategory.CASCADING_FAILURE,
        }
        for rule_id, category in categories_map.items():
            rule = make_rule(id=rule_id, category=category, sequence_number=1)
            assert rule.id == rule_id

    def test_invalid_id_format_rejected(self) -> None:
        with pytest.raises(Exception):
            make_rule(id="invalid-format")

    def test_id_without_sequence_number_rejected(self) -> None:
        with pytest.raises(Exception):
            make_rule(id="unsafe-regex")

    def test_unknown_category_id_rejected(self) -> None:
        with pytest.raises(Exception):
            make_rule(id="unknown-category-001")


class TestSemgrepRuleInvariants:
    def test_false_positive_count_3_requires_auto_disabled(self) -> None:
        with pytest.raises(Exception):
            make_rule(false_positive_count=3, auto_disabled=False)

    def test_false_positive_count_3_with_auto_disabled_ok(self) -> None:
        rule = make_rule(false_positive_count=3, auto_disabled=True)
        assert rule.auto_disabled is True

    def test_synthesized_rule_requires_confidence(self) -> None:
        with pytest.raises(Exception, match="synthesis_confidence"):
            make_rule(source=RuleSource.SYNTHESIZED, synthesis_confidence=None)

    def test_synthesized_rule_with_confidence_ok(self) -> None:
        rule = make_rule(source=RuleSource.SYNTHESIZED, synthesis_confidence=0.85)
        assert rule.synthesis_confidence == 0.85

    def test_manual_rule_without_confidence_ok(self) -> None:
        rule = make_rule(source=RuleSource.MANUAL, synthesis_confidence=None)
        assert rule.synthesis_confidence is None
