"""Unit tests for compute_risk_score — TDD first pass.

Constitution VII: Tests written before implementation. These must FAIL
until risk_score.py is implemented.

Thresholds: LOW < 5 | MEDIUM 5-12 | HIGH > 12
Weights: critical=5, high=3, medium=2, low=1
"""

import pytest
from src.domain.incidents.enums import IncidentSeverity, RiskLevel
from src.domain.scanning.risk_score import (
    SEVERITY_WEIGHTS,
    RiskThresholds,
    compute_risk_score,
    score_to_risk_level,
)


class TestSeverityWeights:
    def test_critical_weight_is_5(self) -> None:
        assert SEVERITY_WEIGHTS[IncidentSeverity.CRITICAL] == 5

    def test_high_weight_is_3(self) -> None:
        assert SEVERITY_WEIGHTS[IncidentSeverity.HIGH] == 3

    def test_medium_weight_is_2(self) -> None:
        assert SEVERITY_WEIGHTS[IncidentSeverity.MEDIUM] == 2

    def test_low_weight_is_1(self) -> None:
        assert SEVERITY_WEIGHTS[IncidentSeverity.LOW] == 1

    def test_all_severities_have_weights(self) -> None:
        for severity in IncidentSeverity:
            assert severity in SEVERITY_WEIGHTS


class TestRiskThresholds:
    def test_low_threshold_upper_bound(self) -> None:
        assert RiskThresholds.LOW_MAX == 4

    def test_medium_threshold_upper_bound(self) -> None:
        assert RiskThresholds.MEDIUM_MAX == 12


class TestComputeRiskScore:
    def test_empty_findings_returns_zero(self) -> None:
        assert compute_risk_score([]) == 0

    def test_single_critical_finding(self) -> None:
        assert compute_risk_score([IncidentSeverity.CRITICAL]) == 5

    def test_single_high_finding(self) -> None:
        assert compute_risk_score([IncidentSeverity.HIGH]) == 3

    def test_single_medium_finding(self) -> None:
        assert compute_risk_score([IncidentSeverity.MEDIUM]) == 2

    def test_single_low_finding(self) -> None:
        assert compute_risk_score([IncidentSeverity.LOW]) == 1

    def test_mixed_findings_sum(self) -> None:
        # critical(5) + high(3) + medium(2) + low(1) = 11
        findings = [
            IncidentSeverity.CRITICAL,
            IncidentSeverity.HIGH,
            IncidentSeverity.MEDIUM,
            IncidentSeverity.LOW,
        ]
        assert compute_risk_score(findings) == 11

    def test_multiple_same_severity(self) -> None:
        # 3 x high = 9
        assert compute_risk_score([IncidentSeverity.HIGH] * 3) == 9

    def test_result_is_integer(self) -> None:
        score = compute_risk_score([IncidentSeverity.CRITICAL])
        assert isinstance(score, int)


class TestScoreToRiskLevel:
    # ── Boundary: LOW (score < 5) ──────────────────────────────────────────
    def test_score_0_is_low(self) -> None:
        assert score_to_risk_level(0) == RiskLevel.LOW

    def test_score_1_is_low(self) -> None:
        assert score_to_risk_level(1) == RiskLevel.LOW

    def test_score_4_is_low(self) -> None:
        assert score_to_risk_level(4) == RiskLevel.LOW

    # ── Boundary: MEDIUM (5 <= score <= 12) ───────────────────────────────
    def test_score_5_is_medium(self) -> None:
        assert score_to_risk_level(5) == RiskLevel.MEDIUM

    def test_score_8_is_medium(self) -> None:
        assert score_to_risk_level(8) == RiskLevel.MEDIUM

    def test_score_12_is_medium(self) -> None:
        assert score_to_risk_level(12) == RiskLevel.MEDIUM

    # ── Boundary: HIGH (score > 12) ───────────────────────────────────────
    def test_score_13_is_high(self) -> None:
        assert score_to_risk_level(13) == RiskLevel.HIGH

    def test_score_20_is_high(self) -> None:
        assert score_to_risk_level(20) == RiskLevel.HIGH

    def test_score_100_is_high(self) -> None:
        assert score_to_risk_level(100) == RiskLevel.HIGH

    # ── Negative score guard ──────────────────────────────────────────────
    def test_negative_score_raises(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            score_to_risk_level(-1)


class TestComputeRiskScoreIntegration:
    """End-to-end: compute score then classify."""

    def test_zero_findings_is_low(self) -> None:
        score = compute_risk_score([])
        assert score_to_risk_level(score) == RiskLevel.LOW

    def test_one_critical_is_medium(self) -> None:
        score = compute_risk_score([IncidentSeverity.CRITICAL])
        assert score_to_risk_level(score) == RiskLevel.MEDIUM

    def test_three_criticals_is_high(self) -> None:
        # 3 x 5 = 15 > 12
        score = compute_risk_score([IncidentSeverity.CRITICAL] * 3)
        assert score_to_risk_level(score) == RiskLevel.HIGH

    def test_threshold_5_boundary_medium(self) -> None:
        # 1 critical(5) = score 5 → MEDIUM
        score = compute_risk_score([IncidentSeverity.CRITICAL])
        assert score == 5
        assert score_to_risk_level(score) == RiskLevel.MEDIUM

    def test_threshold_12_boundary_medium(self) -> None:
        # 4 high(3) = 12 → still MEDIUM
        score = compute_risk_score([IncidentSeverity.HIGH] * 4)
        assert score == 12
        assert score_to_risk_level(score) == RiskLevel.MEDIUM

    def test_threshold_13_boundary_high(self) -> None:
        # 4 high(3) + 1 low(1) = 13 → HIGH
        score = compute_risk_score([IncidentSeverity.HIGH] * 4 + [IncidentSeverity.LOW])
        assert score == 13
        assert score_to_risk_level(score) == RiskLevel.HIGH
