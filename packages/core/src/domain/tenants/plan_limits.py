"""
T157: Plan limit enforcement service.

Centralizes all tier-based rules:
  - Contributor caps (Free: 5 | Team: 25 | Enterprise: unlimited)
  - Repository caps  (Free: 3 | Team: 25 | Enterprise: unlimited)
  - Layer access     (Free: L1 | Team: L1+L2 | Enterprise: L1+L2+L3)
  - Findings retention (Free: 90d | Team: 365d | Enterprise: 730d)

Usage:
    from packages.core.src.domain.tenants.plan_limits import PlanLimits, Plan, Layer

    PlanLimits.check_contributor_limit(Plan.FREE, current_count=4)   # ok
    PlanLimits.check_contributor_limit(Plan.FREE, current_count=5)   # raises PlanLimitError
    PlanLimits.check_layer_access(Plan.TEAM, Layer.L3)               # raises PlanLimitError
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Plan(str, Enum):
    FREE = "free"
    TEAM = "team"
    ENTERPRISE = "enterprise"

    @classmethod
    def from_str(cls, value: str) -> "Plan":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.FREE  # graceful fallback


class Layer(str, Enum):
    L1 = "l1"
    L2 = "l2"
    L3 = "l3"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class PlanLimitError(Exception):
    """Raised when a tenant attempts to exceed their plan's limits."""

    def __init__(
        self,
        message: str,
        code: str = "PLAN_LIMIT_EXCEEDED",
        plan: Plan = Plan.FREE,
        current: int = 0,
        maximum: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.plan = plan
        self.current = current
        self.maximum = maximum


# ---------------------------------------------------------------------------
# Static limit tables
# ---------------------------------------------------------------------------

_MAX_CONTRIBUTORS: dict[Plan, Optional[int]] = {
    Plan.FREE: 5,
    Plan.TEAM: 25,
    Plan.ENTERPRISE: None,  # unlimited
}

_MAX_REPOS: dict[Plan, Optional[int]] = {
    Plan.FREE: 3,
    Plan.TEAM: 25,
    Plan.ENTERPRISE: None,
}

_RETENTION_DAYS: dict[Plan, int] = {
    Plan.FREE: 90,
    Plan.TEAM: 365,
    Plan.ENTERPRISE: 730,
}

# Layers available per plan (inclusive of lower layers)
_LAYER_ACCESS: dict[Plan, frozenset[Layer]] = {
    Plan.FREE: frozenset([Layer.L1]),
    Plan.TEAM: frozenset([Layer.L1, Layer.L2]),
    Plan.ENTERPRISE: frozenset([Layer.L1, Layer.L2, Layer.L3]),
}

# Plan upgrade path for error messages
_UPGRADE_HINT: dict[Plan, str] = {
    Plan.FREE: "Upgrade to the Team plan to unlock this feature.",
    Plan.TEAM: "Upgrade to the Enterprise plan to unlock this feature.",
    Plan.ENTERPRISE: "",
}


# ---------------------------------------------------------------------------
# PlanLimits service
# ---------------------------------------------------------------------------

class PlanLimits:
    """
    Stateless service — all methods are classmethods.
    No DB calls; checks are purely against the static limit tables.
    """

    # ------------------------------------------------------------------
    # Queries (no side effects)
    # ------------------------------------------------------------------

    @classmethod
    def max_contributors(cls, plan: Plan) -> Optional[int]:
        return _MAX_CONTRIBUTORS[plan]

    @classmethod
    def max_repos(cls, plan: Plan) -> Optional[int]:
        return _MAX_REPOS[plan]

    @classmethod
    def retention_days(cls, plan: Plan) -> int:
        return _RETENTION_DAYS[plan]

    @classmethod
    def can_use_layer(cls, plan: Plan, layer: Layer) -> bool:
        return layer in _LAYER_ACCESS[plan]

    # ------------------------------------------------------------------
    # Enforcement (raises PlanLimitError on violation)
    # ------------------------------------------------------------------

    @classmethod
    def check_contributor_limit(cls, plan: Plan, current_count: int) -> None:
        """
        Raise PlanLimitError if adding one more contributor would exceed
        the plan's cap.  ``current_count`` is the CURRENT number of contributors
        (before adding the new one).
        """
        maximum = _MAX_CONTRIBUTORS[plan]
        if maximum is None:
            return  # unlimited

        if current_count >= maximum:
            hint = _UPGRADE_HINT[plan]
            raise PlanLimitError(
                message=(
                    f"Plan limit exceeded: max {maximum} contributors on the "
                    f"{plan.value.capitalize()} plan. {hint}"
                ),
                code="PLAN_LIMIT_EXCEEDED",
                plan=plan,
                current=current_count,
                maximum=maximum,
            )

    @classmethod
    def check_repo_limit(cls, plan: Plan, current_count: int) -> None:
        """
        Raise PlanLimitError if adding one more repository would exceed
        the plan's cap.
        """
        maximum = _MAX_REPOS[plan]
        if maximum is None:
            return

        if current_count >= maximum:
            hint = _UPGRADE_HINT[plan]
            raise PlanLimitError(
                message=(
                    f"Plan limit exceeded: max {maximum} repos on the "
                    f"{plan.value.capitalize()} plan. {hint}"
                ),
                code="PLAN_LIMIT_EXCEEDED",
                plan=plan,
                current=current_count,
                maximum=maximum,
            )

    @classmethod
    def check_layer_access(cls, plan: Plan, layer: Layer) -> None:
        """
        Raise PlanLimitError if the plan does not include access to ``layer``.
        """
        if layer in _LAYER_ACCESS[plan]:
            return

        # Determine the minimum plan that unlocks the layer
        min_plan: Optional[str] = None
        for p in (Plan.FREE, Plan.TEAM, Plan.ENTERPRISE):
            if layer in _LAYER_ACCESS[p]:
                min_plan = p.value.capitalize()
                break

        hint = _UPGRADE_HINT[plan]
        raise PlanLimitError(
            message=(
                f"Plan limit exceeded: Layer {layer.value.upper()} is not available on the "
                f"{plan.value.capitalize()} plan. "
                f"{'Requires at least the ' + min_plan + ' plan. ' if min_plan else ''}"
                f"{hint}"
            ),
            code="PLAN_LIMIT_EXCEEDED",
            plan=plan,
            current=0,
            maximum=None,
        )
