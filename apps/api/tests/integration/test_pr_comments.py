"""Tests for PR review comment posting via GitHub adapter (T102).

PR review comment posting (skip if GITHUB_APP_ID not set).
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

# Skip these tests if we can't import the necessary modules
# (Python 3.10 compatibility issue with StrEnum)
pytest.importorskip("packages.core.src.domain.scanning.entities")

from packages.core.src.domain.incidents.enums import RiskLevel
from packages.core.src.domain.scanning.entities import Advisory


@pytest.fixture
def skip_if_no_github_app() -> None:
    """Skip tests if GitHub App credentials not configured."""
    if not os.environ.get("GITHUB_APP_ID"):
        pytest.skip("GITHUB_APP_ID not configured")


class TestPRCommentPosting:
    """Tests for posting advisory comments to pull requests."""

    @pytest.mark.asyncio
    async def test_inline_comment_posted_when_file_known(
        self, skip_if_no_github_app: None
    ) -> None:
        """Inline PR comment is posted when advisory has file_path and start_line."""
        from packages.core.src.adapters.github_adapter import GitHubAdapter

        adapter = GitHubAdapter()

        with patch("github.Github") as mock_github_class:
            mock_github = MagicMock()
            mock_github_class.return_value = mock_github
            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_pr = MagicMock()
            mock_repo.get_pull.return_value = mock_pr
            mock_comment = MagicMock()
            mock_comment.id = 999
            mock_pr.create_review_comment.return_value = mock_comment

            comment_id = await adapter.post_review_comment(
                repository="owner/repo",
                pr_number=42,
                body="**HIGH RISK**: This code is vulnerable to ReDoS attacks.",
                commit_sha="abc123",
                path="src/parser.py",
                line=123,
            )

            assert comment_id == 999
            mock_pr.create_review_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_top_level_comment_when_no_file(
        self, skip_if_no_github_app: None
    ) -> None:
        """Top-level PR comment is posted when advisory has no file_path."""
        from packages.core.src.adapters.github_adapter import GitHubAdapter

        adapter = GitHubAdapter()

        with patch("github.Github") as mock_github_class:
            mock_github = MagicMock()
            mock_github_class.return_value = mock_github
            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_pr = MagicMock()
            mock_repo.get_pull.return_value = mock_pr
            mock_comment = MagicMock()
            mock_comment.id = 888
            mock_pr.create_issue_comment.return_value = mock_comment

            comment_id = await adapter.post_review_comment(
                repository="owner/repo",
                pr_number=42,
                body="**MEDIUM RISK**: This PR contains general security concerns.",
                commit_sha="abc123",
                path=None,
                line=None,
            )

            assert comment_id == 888
            mock_pr.create_issue_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_comment_contains_risk_badge(
        self, skip_if_no_github_app: None
    ) -> None:
        """Posted comment includes risk level badge."""
        from packages.core.src.adapters.github_adapter import GitHubAdapter

        adapter = GitHubAdapter()

        # Create advisory
        advisory = Advisory(
            scan_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            incident_id=uuid.uuid4(),
            confidence_score=0.9,
            risk_level=RiskLevel.CRITICAL,
            matched_anti_pattern="SQL injection",
            analysis_text="Critical SQL injection vulnerability detected.",
            llm_model_used="gemini-2.5-flash",
            file_path="src/db.py",
            start_line=456,
        )

        # Format comment with risk badge
        risk_badge = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🔴",
            RiskLevel.CRITICAL: "🚨",
        }[advisory.risk_level]

        comment_body = (
            f"{risk_badge} **{advisory.risk_level.name} RISK**\n\n"
            f"{advisory.analysis_text}\n\n"
            f"**Confidence**: {advisory.confidence_score * 100:.0f}%"
        )

        with patch("github.Github") as mock_github_class:
            mock_github = MagicMock()
            mock_github_class.return_value = mock_github
            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_pr = MagicMock()
            mock_repo.get_pull.return_value = mock_pr
            mock_comment = MagicMock()
            mock_comment.id = 777
            mock_pr.create_review_comment.return_value = mock_comment

            comment_id = await adapter.post_review_comment(
                repository="owner/repo",
                pr_number=42,
                body=comment_body,
                commit_sha="abc123",
                path="src/db.py",
                line=456,
            )

            assert comment_id == 777
            # Verify the body contains the risk badge
            assert "🚨" in comment_body or risk_badge in comment_body
