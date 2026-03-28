"""Tests for API key authentication middleware (T126, T129).

API key validation unit tests.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from apps.api.src.middleware.auth import register_api_key, require_api_key


class TestAPIKeyValidation:
    """Tests for API key validation and tenant resolution."""

    @pytest.mark.asyncio
    async def test_valid_api_key_resolves_tenant(self) -> None:
        """Valid API key returns tenant_id in resolved dict."""
        # Setup
        register_api_key("test-key-free", "tenant-free-001", "free")

        # Mock FastAPI Request
        class MockRequest:
            pass

        request = MockRequest()

        # Call with header
        result = await require_api_key(request, x_api_key="test-key-free")

        assert result["tenant_id"] == "tenant-free-001"
        assert result["tier"] == "free"

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self) -> None:
        """Missing X-API-Key header raises HTTPException with 401."""

        class MockRequest:
            pass

        request = MockRequest()

        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(request, x_api_key=None)

        assert exc_info.value.status_code == 401
        assert "Missing X-API-Key header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self) -> None:
        """Invalid API key raises HTTPException with 401."""

        class MockRequest:
            pass

        request = MockRequest()

        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(request, x_api_key="invalid-key-xyz")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_api_key_with_tenant_tier(self) -> None:
        """Resolved key includes tier field (free/team/enterprise)."""
        register_api_key("test-key-team", "tenant-team-001", "team")

        class MockRequest:
            pass

        request = MockRequest()

        result = await require_api_key(request, x_api_key="test-key-team")

        assert result["tenant_id"] == "tenant-team-001"
        assert result["tier"] == "team"

    @pytest.mark.asyncio
    async def test_api_key_enterprise_tier(self) -> None:
        """Enterprise tier keys are properly resolved."""
        register_api_key("test-key-enterprise", "tenant-ent-001", "enterprise")

        class MockRequest:
            pass

        request = MockRequest()

        result = await require_api_key(request, x_api_key="test-key-enterprise")

        assert result["tier"] == "enterprise"
