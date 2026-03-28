"""Tests for REST API SARIF 2.1.0 response format (T128, T130).

SARIF content negotiation and schema validation tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.src.main import create_app
from apps.api.src.middleware.auth import register_api_key


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


class TestSARIFResponse:
    """Tests for SARIF 2.1.0 format response."""

    def test_post_scan_accept_sarif_returns_sarif(self, client: TestClient) -> None:
        """Accept: application/sarif+json returns SARIF response."""
        response = client.post(
            "/v1/scans",
            headers={
                "X-API-Key": "test-key-free",
                "Accept": "application/sarif+json",
            },
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        assert response.status_code == 200
        assert "application/sarif+json" in response.headers.get("content-type", "")
        body = response.json()
        assert "version" in body
        assert body["version"] == "2.1.0"
        assert "runs" in body
        assert isinstance(body["runs"], list)

    def test_sarif_has_correct_schema(self, client: TestClient) -> None:
        """SARIF response has $schema, version, and runs[0].tool.driver.name."""
        response = client.post(
            "/v1/scans",
            headers={
                "X-API-Key": "test-key-free",
                "Accept": "application/sarif+json",
            },
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        body = response.json()
        assert "$schema" in body
        assert "schemastore.azurewebsites.net" in body["$schema"]
        assert body["version"] == "2.1.0"
        assert len(body["runs"]) > 0
        assert body["runs"][0]["tool"]["driver"]["name"] == "oute-muscle"

    def test_sarif_results_match_findings(self, client: TestClient) -> None:
        """SARIF results array matches findings from L1."""
        # First get JSON response to see findings
        response_json = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-free"},
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )
        json_body = response_json.json()
        finding_count = len(json_body["findings"])

        # Then get SARIF response
        response_sarif = client.post(
            "/v1/scans",
            headers={
                "X-API-Key": "test-key-free",
                "Accept": "application/sarif+json",
            },
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )
        sarif_body = response_sarif.json()
        result_count = len(sarif_body["runs"][0]["results"])

        # Both should have same number of items (when diff is non-empty, should have findings)
        assert finding_count == result_count

    def test_sarif_default_accept_returns_json(self, client: TestClient) -> None:
        """Default Accept header (no explicit Accept) returns JSON not SARIF."""
        response = client.post(
            "/v1/scans",
            headers={"X-API-Key": "test-key-free"},
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        assert "application/json" in response.headers.get("content-type", "")
        body = response.json()
        # JSON response should have findings, not runs
        assert "findings" in body
        assert "runs" not in body

    def test_sarif_has_rules_section(self, client: TestClient) -> None:
        """SARIF response includes rules section in driver."""
        response = client.post(
            "/v1/scans",
            headers={
                "X-API-Key": "test-key-free",
                "Accept": "application/sarif+json",
            },
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        body = response.json()
        rules = body["runs"][0]["tool"]["driver"]["rules"]
        assert isinstance(rules, list)

    def test_sarif_results_have_locations(self, client: TestClient) -> None:
        """SARIF results include physical location information."""
        response = client.post(
            "/v1/scans",
            headers={
                "X-API-Key": "test-key-free",
                "Accept": "application/sarif+json",
            },
            json={
                "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
                "repository": "org/repo",
            },
        )

        body = response.json()
        results = body["runs"][0]["results"]
        if results:  # Only check if there are results
            result = results[0]
            assert "locations" in result
            assert len(result["locations"]) > 0
            location = result["locations"][0]
            assert "physicalLocation" in location
            assert "artifactLocation" in location["physicalLocation"]
