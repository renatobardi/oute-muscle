"""
T153: Unit tests for plan limit enforcement.
Tests: contributor cap, repo cap, layer access (L1/L2/L3), all three tiers.
"""

import pytest

from packages.core.src.domain.tenants.plan_limits import (
    Layer,
    Plan,
    PlanLimitError,
    PlanLimits,
)

# ---------------------------------------------------------------------------
# PlanLimits static config
# ---------------------------------------------------------------------------


class TestPlanLimitsConfig:
    def test_free_contributor_limit(self):
        assert PlanLimits.max_contributors(Plan.FREE) == 5

    def test_team_contributor_limit(self):
        assert PlanLimits.max_contributors(Plan.TEAM) == 25

    def test_enterprise_contributor_limit_is_unlimited(self):
        assert PlanLimits.max_contributors(Plan.ENTERPRISE) is None

    def test_free_repo_limit(self):
        assert PlanLimits.max_repos(Plan.FREE) == 3

    def test_team_repo_limit(self):
        assert PlanLimits.max_repos(Plan.TEAM) == 25

    def test_enterprise_repo_limit_is_unlimited(self):
        assert PlanLimits.max_repos(Plan.ENTERPRISE) is None

    def test_findings_retention_days_free(self):
        assert PlanLimits.retention_days(Plan.FREE) == 90

    def test_findings_retention_days_team(self):
        assert PlanLimits.retention_days(Plan.TEAM) == 365

    def test_findings_retention_days_enterprise(self):
        assert PlanLimits.retention_days(Plan.ENTERPRISE) == 730


# ---------------------------------------------------------------------------
# Layer access
# ---------------------------------------------------------------------------


class TestLayerAccess:
    def test_free_has_layer1_only(self):
        assert PlanLimits.can_use_layer(Plan.FREE, Layer.L1) is True
        assert PlanLimits.can_use_layer(Plan.FREE, Layer.L2) is False
        assert PlanLimits.can_use_layer(Plan.FREE, Layer.L3) is False

    def test_team_has_l1_and_l2(self):
        assert PlanLimits.can_use_layer(Plan.TEAM, Layer.L1) is True
        assert PlanLimits.can_use_layer(Plan.TEAM, Layer.L2) is True
        assert PlanLimits.can_use_layer(Plan.TEAM, Layer.L3) is False

    def test_enterprise_has_all_layers(self):
        assert PlanLimits.can_use_layer(Plan.ENTERPRISE, Layer.L1) is True
        assert PlanLimits.can_use_layer(Plan.ENTERPRISE, Layer.L2) is True
        assert PlanLimits.can_use_layer(Plan.ENTERPRISE, Layer.L3) is True


# ---------------------------------------------------------------------------
# Enforcement — contributor cap
# ---------------------------------------------------------------------------


class TestContributorEnforcement:
    def test_adding_contributor_within_limit_passes(self):
        """Should not raise when current count is below the limit."""
        PlanLimits.check_contributor_limit(plan=Plan.FREE, current_count=4)

    def test_adding_contributor_at_exact_limit_raises(self):
        """Should raise when current count equals the limit."""
        with pytest.raises(PlanLimitError) as exc:
            PlanLimits.check_contributor_limit(plan=Plan.FREE, current_count=5)
        assert exc.value.code == "PLAN_LIMIT_EXCEEDED"
        assert "contributor" in str(exc.value).lower()

    def test_adding_contributor_over_limit_raises(self):
        with pytest.raises(PlanLimitError):
            PlanLimits.check_contributor_limit(plan=Plan.FREE, current_count=6)

    def test_team_contributor_limit_allows_up_to_24(self):
        PlanLimits.check_contributor_limit(plan=Plan.TEAM, current_count=24)

    def test_team_contributor_limit_blocks_at_25(self):
        with pytest.raises(PlanLimitError):
            PlanLimits.check_contributor_limit(plan=Plan.TEAM, current_count=25)

    def test_enterprise_never_blocks(self):
        """Enterprise has no contributor cap."""
        PlanLimits.check_contributor_limit(plan=Plan.ENTERPRISE, current_count=10_000)


# ---------------------------------------------------------------------------
# Enforcement — repo cap
# ---------------------------------------------------------------------------


class TestRepoEnforcement:
    def test_free_allows_up_to_2_repos(self):
        PlanLimits.check_repo_limit(plan=Plan.FREE, current_count=2)

    def test_free_blocks_at_3_repos(self):
        with pytest.raises(PlanLimitError) as exc:
            PlanLimits.check_repo_limit(plan=Plan.FREE, current_count=3)
        assert exc.value.code == "PLAN_LIMIT_EXCEEDED"
        assert "repo" in str(exc.value).lower()

    def test_team_allows_up_to_24_repos(self):
        PlanLimits.check_repo_limit(plan=Plan.TEAM, current_count=24)

    def test_team_blocks_at_25_repos(self):
        with pytest.raises(PlanLimitError):
            PlanLimits.check_repo_limit(plan=Plan.TEAM, current_count=25)

    def test_enterprise_never_blocks_repos(self):
        PlanLimits.check_repo_limit(plan=Plan.ENTERPRISE, current_count=1_000)


# ---------------------------------------------------------------------------
# Enforcement — layer access
# ---------------------------------------------------------------------------


class TestLayerEnforcement:
    def test_free_requesting_l2_raises(self):
        with pytest.raises(PlanLimitError) as exc:
            PlanLimits.check_layer_access(plan=Plan.FREE, layer=Layer.L2)
        assert exc.value.code == "PLAN_LIMIT_EXCEEDED"
        assert "layer" in str(exc.value).lower() or "l2" in str(exc.value).lower()

    def test_free_requesting_l3_raises(self):
        with pytest.raises(PlanLimitError):
            PlanLimits.check_layer_access(plan=Plan.FREE, layer=Layer.L3)

    def test_team_requesting_l2_passes(self):
        PlanLimits.check_layer_access(plan=Plan.TEAM, layer=Layer.L2)

    def test_team_requesting_l3_raises(self):
        with pytest.raises(PlanLimitError):
            PlanLimits.check_layer_access(plan=Plan.TEAM, layer=Layer.L3)

    def test_enterprise_all_layers_pass(self):
        PlanLimits.check_layer_access(plan=Plan.ENTERPRISE, layer=Layer.L1)
        PlanLimits.check_layer_access(plan=Plan.ENTERPRISE, layer=Layer.L2)
        PlanLimits.check_layer_access(plan=Plan.ENTERPRISE, layer=Layer.L3)

    def test_all_tiers_allow_l1(self):
        for plan in (Plan.FREE, Plan.TEAM, Plan.ENTERPRISE):
            PlanLimits.check_layer_access(plan=plan, layer=Layer.L1)  # must not raise


# ---------------------------------------------------------------------------
# PlanLimitError fields
# ---------------------------------------------------------------------------


class TestPlanLimitError:
    def test_error_includes_current_and_max(self):
        with pytest.raises(PlanLimitError) as exc:
            PlanLimits.check_contributor_limit(plan=Plan.FREE, current_count=5)
        err = exc.value
        assert err.current == 5
        assert err.maximum == 5
        assert err.plan == Plan.FREE

    def test_error_includes_upgrade_hint(self):
        with pytest.raises(PlanLimitError) as exc:
            PlanLimits.check_layer_access(plan=Plan.FREE, layer=Layer.L2)
        assert "team" in str(exc.value).lower() or "upgrade" in str(exc.value).lower()
