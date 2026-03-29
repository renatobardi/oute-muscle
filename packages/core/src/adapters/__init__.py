"""Adapter implementations of ports.

Real DB adapters live in packages/db/src/adapters/ (SQLAlchemy dependency).
Real Vertex AI adapters live in apps/api/src/adapters/ (GCP dependency).
Only the GitHub adapter lives here (pure PyGithub, no heavy infra deps).
"""

from .github_adapter import GitHubAdapter

__all__ = [
    "GitHubAdapter",
]
