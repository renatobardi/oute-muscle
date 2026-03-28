"""PyGithub adapter implementing GitHubPort (T103).

Uses PyGithub library (github.Github).
Authentication via GitHub App private key (env: GITHUB_APP_PRIVATE_KEY, GITHUB_APP_ID).
If env vars not set → skip gracefully.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ..ports.github import CheckRunResult, GitHubError, GitHubNotFoundError, PullRequestDiff

logger = logging.getLogger(__name__)


class GitHubAdapter:
    """PyGithub adapter for GitHub App API access."""

    def __init__(self) -> None:
        """Initialize adapter with GitHub App credentials from environment.

        If credentials not set, methods will raise GitHubError.
        """
        self.app_id: str | None = os.environ.get("GITHUB_APP_ID")
        self.private_key: str | None = os.environ.get("GITHUB_APP_PRIVATE_KEY")

        if not self.app_id or not self.private_key:
            logger.warning("GitHub App credentials not configured; adapter will fail gracefully")

    def _get_client(self) -> Any:
        """Get authenticated GitHub client.

        Raises:
            GitHubError: If credentials not configured.
        """
        if not self.app_id or not self.private_key:
            raise GitHubError(
                "GitHub App credentials not configured (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY)"
            )

        try:
            from github import Github
            from github.GithubIntegration import GithubIntegration  # noqa: F401
        except ImportError as e:
            raise GitHubError("PyGithub not installed. Install with: pip install PyGithub") from e

        # TODO: Get installation ID from webhook payload
        # For now, return a base client
        return Github()

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
            max_lines: Truncation limit (default 3000 lines).

        Returns:
            Parsed diff with truncation flag if applicable.

        Raises:
            GitHubNotFoundError: If repo or PR does not exist.
            GitHubError: For other API failures.
        """
        try:
            from github import GithubException
        except ImportError as e:
            raise GitHubError("PyGithub not installed") from e

        try:
            client = self._get_client()
            repo = client.get_repo(repository)
            pr = repo.get_pull(pr_number)

            # Get PR files and build unified diff
            diff_lines: list[str] = []
            commit_sha = pr.head.sha

            for file in pr.get_files():
                # Add file header
                diff_lines.append(f"diff --git a/{file.filename} b/{file.filename}")
                diff_lines.append(f"index {file.sha[:7]}..{file.sha[:7]} 100644")
                diff_lines.append(f"--- a/{file.filename}")
                diff_lines.append(f"+++ b/{file.filename}")

                # Add patch if available
                if file.patch:
                    diff_lines.extend(file.patch.splitlines())

            # Truncate if needed
            diff_content = "\n".join(diff_lines)
            truncated = len(diff_lines) > max_lines
            if truncated:
                diff_content = "\n".join(diff_lines[:max_lines])

            return PullRequestDiff(
                repository=repository,
                pr_number=pr_number,
                commit_sha=commit_sha,
                diff_content=diff_content,
                diff_lines=len(diff_lines),
                truncated=truncated,
            )

        except GithubException as e:
            if e.status == 404:
                raise GitHubNotFoundError(
                    f"Repository or PR not found: {repository}#{pr_number}"
                ) from e
            raise GitHubError(f"GitHub API error: {e}") from e
        except Exception as e:
            raise GitHubError(f"Failed to fetch PR diff: {e}") from e

    async def create_check_run(
        self,
        repository: str,
        commit_sha: str,
        *,
        name: str,
        conclusion: str,
        title: str,
        summary: str,
        annotations: list[dict] | None = None,
    ) -> CheckRunResult:
        """Create or update a Check Run with SARIF-style annotations.

        Args:
            repository: Full repo name e.g. 'owner/repo'.
            commit_sha: Commit SHA to attach check run to.
            name: Check run name.
            conclusion: 'success' | 'failure' | 'neutral'.
            title: Check run title.
            summary: Check run summary text.
            annotations: List of SARIF-style annotations.

        Returns:
            CheckRunResult with ID and URL.

        Raises:
            GitHubError: If the API call fails.
        """
        try:
            from github import GithubException
        except ImportError as e:
            raise GitHubError("PyGithub not installed") from e

        try:
            client = self._get_client()
            repo = client.get_repo(repository)

            check_run = repo.create_check_run(
                name=name,
                head_sha=commit_sha,
                conclusion=conclusion,
                status="completed",
                output={
                    "title": title,
                    "summary": summary,
                    "annotations": annotations or [],
                },
            )

            return CheckRunResult(
                check_run_id=check_run.id,
                html_url=check_run.html_url,
            )

        except GithubException as e:
            raise GitHubError(f"Failed to create check run: {e}") from e
        except Exception as e:
            raise GitHubError(f"Unexpected error creating check run: {e}") from e

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
            repository: Full repo name e.g. 'owner/repo'.
            pr_number: The pull request number.
            body: Comment body (markdown).
            commit_sha: Commit SHA for context.
            path: File path for inline comment; None for top-level PR comment.
            line: Line number for inline comment; None for top-level.

        Returns:
            GitHub comment ID.

        Raises:
            GitHubError: If the API call fails.
        """
        try:
            from github import GithubException
        except ImportError as e:
            raise GitHubError("PyGithub not installed") from e

        try:
            client = self._get_client()
            repo = client.get_repo(repository)
            pr = repo.get_pull(pr_number)

            if path is not None and line is not None:
                # Post inline review comment
                comment = pr.create_review_comment(
                    body=body,
                    commit_id=commit_sha,
                    path=path,
                    line=line,
                )
            else:
                # Post top-level PR comment
                comment = pr.create_issue_comment(body=body)

            return comment.id

        except GithubException as e:
            raise GitHubError(f"Failed to post review comment: {e}") from e
        except Exception as e:
            raise GitHubError(f"Unexpected error posting review comment: {e}") from e

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

        Args:
            repository: Full repo name e.g. 'owner/repo'.
            title: PR title.
            body: PR description (markdown).
            head: Head branch name.
            base: Base branch name (default: main).

        Returns:
            PR URL (e.g., https://github.com/owner/repo/pull/123).

        Raises:
            GitHubError: If the API call fails.
        """
        try:
            from github import GithubException
        except ImportError as e:
            raise GitHubError("PyGithub not installed") from e

        try:
            client = self._get_client()
            repo = client.get_repo(repository)

            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
            )

            return pr.html_url

        except GithubException as e:
            raise GitHubError(f"Failed to create pull request: {e}") from e
        except Exception as e:
            raise GitHubError(f"Unexpected error creating pull request: {e}") from e
