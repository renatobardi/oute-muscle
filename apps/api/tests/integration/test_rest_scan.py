"""Tests for REST API POST /scans endpoint with JSON response (T127).

Integration tests using FastAPI TestClient.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.src.main import create_app
from apps.api.src.middleware.auth import register_api_key

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> TestClient:
    """Create test client with fresh app instance."""
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_keys() -> None:
    """Register test API keys before each test."""
    register_api_key("test-key-free", "tenant-free-001", "free")
    register_api_key("test-key-team", "tenant-team-001", "team")


class TestPostScanJSON:
    """Tests for POST /scans with JSON response."""

    def test_post_scan_with_api_key_returns_findings(self, client: TestClient) -> None:
        """POST with diff + X-API-Key returns 200 JSON with scan_id, findings, risk_level."""
        response = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-free"},
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -1,1 +1,1 @@",
                "repository": "org/repo",
                "commit_sha": "abc123def456",
                "pr_number": 42,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "scan_id" in body
        assert isinstance(body["scan_id"], str)
        assert "findings" in body
        assert isinstance(body["findings"], list)
        assert "risk_level" in body
        assert body["risk_level"] in ("low", "medium", "high", "critical")

    def test_post_scan_missing_api_key_returns_401(self, client: TestClient) -> None:
        """No X-API-Key header returns 401."""
        response = client.post(
            "/v1/scans",
            json={
                "diff": "--- a/src/utils.py",
                "repository": "org/repo",
            },
        )

        assert response.status_code == 401

    def test_post_scan_diff_required(self, client: TestClient) -> None:
        """Empty/missing diff returns 422 validation error."""
        response = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-free"},
            json={
                "diff": "",  # Empty diff
                "repository": "org/repo",
            },
        )

        assert response.status_code == 422

    def test_post_scan_response_schema(self, client: TestClient) -> None:
        """Response matches ScanCreateResponse schema."""
        response = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-team"},
            json={
                "diff": "--- a/file.py\n+++ b/file.py",
                "repository": "org/repo",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert all(
            k in body for k in ["scan_id", "findings", "advisories", "risk_level", "duration_ms"]
        )
        assert isinstance(body["advisories"], list)
        assert isinstance(body["duration_ms"], int)

    def test_post_scan_tier_free_no_advisories(self, client: TestClient) -> None:
        """Free tier returns no advisories (L1 only)."""
        response = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-free"},
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        body = response.json()
        assert body["advisories"] == []

    def test_post_scan_tier_team_may_have_advisories(self, client: TestClient) -> None:
        """Team tier may include advisories (L1 + L2 ready)."""
        response = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-team"},
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        body = response.json()
        assert isinstance(body["advisories"], list)
