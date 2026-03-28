"""Composite risk score computation for Layer 2 scan analysis.

Formula (integer arithmetic only — no division, no fractions):
  score = sum(SEVERITY_WEIGHTS[finding] for finding in findings)

Thresholds:
  LOW    — score in [0, 4]    (score < 5)
  MEDIUM — score in [5, 12]   (5 <= score <= 12)
  HIGH   — score in [13, ∞)   (score > 12)

Weights:
  critical = 5
  high     = 3
  medium   = 2
  low      = 1
"""

from ..incidents.enums import IncidentSeverity, RiskLevel


SEVERITY_WEIGHTS: dict[IncidentSeverity, int] = {
    IncidentSeverity.CRITICAL: 5,
    IncidentSeverity.HIGH: 3,
    IncidentSeverity.MEDIUM: 2,
    IncidentSeverity.LOW: 1,
}


class RiskThresholds:
    """Integer boundaries for risk level classification (class-level constants)."""

    LOW_MAX: int = 4  # score <= LOW_MAX → LOW
    MEDIUM_MAX: int = 12  # LOW_MAX < score <= MEDIUM_MAX → MEDIUM; > MEDIUM_MAX → HIGH


def compute_risk_score(findings: list[IncidentSeverity]) -> int:
    """Compute the composite risk score from a list of finding severities.

    Uses integer arithmetic only (no division or fractional components).

    Args:
        findings: List of severity values from Layer 1 findings.

    Returns:
        Non-negative integer risk score.
    """
    return sum(SEVERITY_WEIGHTS[severity] for severity in findings)


def score_to_risk_level(score: int) -> RiskLevel:
    """Classify an integer risk score into a RiskLevel.

    Args:
        score: Non-negative integer risk score from compute_risk_score.

    Returns:
        RiskLevel enum value.

    Raises:
        ValueError: If score is negative.
    """
    if score < 0:
        raise ValueError(f"Risk score cannot be negative, got {score}")
    if score <= 4:
        return RiskLevel.LOW
    if score <= 12:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH
