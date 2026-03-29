"""GitHub port — abstracts GitHub App API interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PullRequestDiff:
    """Parsed diff from a GitHub pull request."""

    repository: str
    pr_number: int
    commit_sha: str
    diff_content: str
    diff_lines: int
    truncated: bool  # True if diff exceeded 3000-line limit


@dataclass(frozen=True)
class CheckRunResult:
    """Result of creating or updating a GitHub Check Run."""

    check_run_id: int
    html_url: str


@runtime_checkable
class GitHubPort(Protocol):
    """Port for GitHub App API. Implemented by PyGithub adapter."""

    async def get_pr_diff(
        self,
        repository: str,
        pr_number: int,
        *,
        max_lines: int = 3000,
    ) -> PullRequestDiff:
        """Fetch and return the diff for a pull request.

        Args:
            repository: Full repo name e.g. 'owner/repo'.
            pr_number: The pull request number.
            max_lines: Truncation limit (Constitution spec: 3000 lines).

        Returns:
            Parsed diff with truncation flag if applicable.

        Raises:
            GitHubNotFoundError: If repo or PR does not exist.
            GitHubError: For other API failures.
        """
        ...

    async def create_check_run(
        self,
        repository: str,
        commit_sha: str,
        *,
        name: str,
        conclusion: str,  # 'success' | 'failure' | 'neutral'
        title: str,
        summary: str,
        annotations: list[dict[str, Any]] | None = None,
    ) -> CheckRunResult:
        """Create or update a Check Run with SARIF-style annotations.

        Raises:
            GitHubError: If the API call fails.
        """
        ...

    async def post_review_comment(
        self,
        repository: str,
        pr_number: int,
        body: str,
        *,
        commit_sha: str,
        path: str | None = None,
        line: int | None = None,
    ) -> int:
        """Post a review comment on a PR (inline or top-level).

        Args:
            path: File path for inline comment; None for top-level PR comment.
            line: Line number for inline comment; None for top-level.

        Returns:
            GitHub comment ID.

        Raises:
            GitHubError: If the API call fails.
        """
        ...

    async def create_pr(
        self,
        repository: str,
        *,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        """Create a pull request and return its URL.

        Used by the synthesis worker (Layer 3) to open candidate rule PRs.
        """
        ...


class GitHubError(Exception):
    """Base error for GitHub port failures."""


class GitHubNotFoundError(GitHubError):
    """Raised when a repository or PR is not found."""
