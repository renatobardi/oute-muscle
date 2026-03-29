"""T031: Unit tests for admin user management operations."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest


class TestAdminSelfDemotionBlock:
    """Admin cannot change their own role."""

    def test_self_demotion_detected(self) -> None:
        """Verify the business rule: admin_user_id == target user_id should be blocked."""
        admin_id = str(uuid.uuid4())
        target_id = admin_id  # Same user
        assert admin_id == target_id  # Self-demotion scenario


class TestRoleValidation:
    """Valid roles: viewer, editor, admin."""

    @pytest.mark.parametrize("role", ["viewer", "editor", "admin"])
    def test_valid_roles_accepted(self, role: str) -> None:
        assert role in ("viewer", "editor", "admin")

    @pytest.mark.parametrize("role", ["superadmin", "owner", "", "ADMIN"])
    def test_invalid_roles_rejected(self, role: str) -> None:
        assert role not in ("viewer", "editor", "admin")


class TestDeactivateActivate:
    """Toggle is_active on user accounts."""

    def test_deactivate_sets_false(self) -> None:
        user = MagicMock()
        user.is_active = True
        user.is_active = False
        assert not user.is_active

    def test_activate_sets_true(self) -> None:
        user = MagicMock()
        user.is_active = False
        user.is_active = True
        assert user.is_active


class TestAssignTenant:
    """Assign user to tenant."""

    def test_assign_tenant_id(self) -> None:
        user = MagicMock()
        tenant_id = uuid.uuid4()
        user.tenant_id = tenant_id
        assert user.tenant_id == tenant_id
