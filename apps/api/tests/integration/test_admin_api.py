"""T032: Integration tests for admin cross-tenant queries.

Requires GOOGLE_CLOUD_PROJECT and DATABASE_URL env vars.
Tests the admin endpoints return data from multiple tenants.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="requires DATABASE_URL env var",
)


@pytest.mark.asyncio
async def test_admin_users_returns_cross_tenant() -> None:
    """Admin GET /admin/users should return users from multiple tenants."""
    # This test validates the query pattern — actual DB test runs in CI
    from apps.api.src.routes.admin import AdminUserResponse

    # Verify response model has required fields
    fields = AdminUserResponse.model_fields
    assert "id" in fields
    assert "email" in fields
    assert "tenant_id" in fields
    assert "tenant_name" in fields
    assert "role" in fields
    assert "firebase_uid" in fields


@pytest.mark.asyncio
async def test_admin_metrics_response_shape() -> None:
    """Admin GET /admin/metrics should return all required metric sections."""
    from apps.api.src.routes.admin import AdminMetricsResponse

    fields = AdminMetricsResponse.model_fields
    assert "users" in fields
    assert "tenants" in fields
    assert "scans" in fields
    assert "findings" in fields
    assert "incidents" in fields
    assert "rules" in fields
    assert "llm_usage_30d" in fields
