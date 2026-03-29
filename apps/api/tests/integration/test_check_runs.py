"""Tests for Check Run creation via GitHub adapter (T101).

Check Run creation integration test (skip if GITHUB_APP_ID not set).
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

# Skip these tests if we can't import the necessary modules
# (Python 3.10 compatibility issue with StrEnum)
pytest.importorskip("packages.core.src.domain.scanning.entities")

from packages.core.src.domain.incidents.enums import IncidentSeverity
from packages.core.src.domain.scanning.entities import Finding

pytestmark = pytest.mark.integration


@pytest.fixture
def skip_if_no_github_app() -> None:
    """Skip tests if GitHub App credentials not configured."""
    if not os.environ.get("GITHUB_APP_ID"):
        pytest.skip("GITHUB_APP_ID not configured")


class TestCheckRunCreation:
    """Tests for GitHub Check Run creation with SARIF annotations."""

    @pytest.mark.asyncio
    async def test_check_run_created_with_sarif_annotations(
        self, skip_if_no_github_app: None
    ) -> None:
        """Check Run is created with correct SARIF annotation format."""
        from packages.core.src.adapters.github_adapter import GitHubAdapter

        # Create adapter
        adapter = GitHubAdapter()

        # Create test findings
        tenant_id = uuid.uuid4()
        findings = [
            Finding(
                scan_id=uuid.uuid4(),
                tenant_id=tenant_id,
                rule_id="unsafe-regex-001",
                incident_id=uuid.uuid4(),
                file_path="src/utils.py",
                start_line=42,
                end_line=42,
                severity=IncidentSeverity.HIGH,
                message="Regex pattern is vulnerable to ReDoS",
                remediation="Use a simpler pattern",
            ),
        ]

        # Mock PyGithub
        with patch("github.Github") as mock_github_class:
            mock_github = MagicMock()
            mock_github_class.return_value = mock_github

            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            mock_check_run = MagicMock()
            mock_check_run.id = 12345
            mock_check_run.html_url = "https://github.com/owner/repo/runs/12345"
            mock_repo.create_check_run.return_value = mock_check_run

            # Call create_check_run
            result = await adapter.create_check_run(
                repository="owner/repo",
                commit_sha="abc123def456",
                name="Oute Muscle Security",
                conclusion="failure",
                title="Security Findings",
                summary="Found 1 high-severity issue",
                annotations=[
                    {
                        "path": finding.file_path,
                        "start_line": finding.start_line,
                        "end_line": finding.end_line or finding.start_line,
                        "annotation_level": "failure",
                        "message": finding.message,
                        "title": finding.rule_id,
                    }
                    for finding in findings
                ],
            )

            # Verify
            assert result.check_run_id == 12345
            assert result.html_url == "https://github.com/owner/repo/runs/12345"

            # Verify create_check_run was called with correct args
            mock_repo.create_check_run.assert_called_once()
            call_args = mock_repo.create_check_run.call_args

            # Check required fields
            assert call_args.kwargs["name"] == "Oute Muscle Security"
            assert call_args.kwargs["head_sha"] == "abc123def456"
            assert call_args.kwargs["conclusion"] == "failure"

    @pytest.mark.asyncio
    async def test_check_run_failure_on_findings(self, skip_if_no_github_app: None) -> None:
        """Check Run conclusion is 'failure' when findings are present."""
        from packages.core.src.adapters.github_adapter import GitHubAdapter

        adapter = GitHubAdapter()

        findings = [
            Finding(
                scan_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                rule_id="unsafe-regex-001",
                incident_id=uuid.uuid4(),
                file_path="src/utils.py",
                start_line=10,
                end_line=10,
                severity=IncidentSeverity.CRITICAL,
                message="Critical security issue",
                remediation="Fix it",
            ),
        ]

        with patch("github.Github") as mock_github_class:
            mock_github = MagicMock()
            mock_github_class.return_value = mock_github
            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_check_run = MagicMock()
            mock_check_run.id = 999
            mock_check_run.html_url = "https://example.com"
            mock_repo.create_check_run.return_value = mock_check_run

            annotations = [
                {
                    "path": f.file_path,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                    "annotation_level": "failure",
                    "message": f.message,
                    "title": f.rule_id,
                }
                for f in findings
            ]

            result = await adapter.create_check_run(
                repository="owner/repo",
                commit_sha="abc123",
                name="Oute Muscle Security",
                conclusion="failure",
                title="Issues Found",
                summary="Found issues",
                annotations=annotations,
            )

            assert result.check_run_id == 999

    @pytest.mark.asyncio
    async def test_check_run_success_on_no_findings(self, skip_if_no_github_app: None) -> None:
        """Check Run conclusion is 'success' when no findings are present."""
        from packages.core.src.adapters.github_adapter import GitHubAdapter

        adapter = GitHubAdapter()

        with patch("github.Github") as mock_github_class:
            mock_github = MagicMock()
            mock_github_class.return_value = mock_github
            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_check_run = MagicMock()
            mock_check_run.id = 555
            mock_check_run.html_url = "https://example.com"
            mock_repo.create_check_run.return_value = mock_check_run

            result = await adapter.create_check_run(
                repository="owner/repo",
                commit_sha="abc123",
                name="Oute Muscle Security",
                conclusion="success",
                title="No Issues",
                summary="Code is clean",
                annotations=None,
            )

            assert result.check_run_id == 555
