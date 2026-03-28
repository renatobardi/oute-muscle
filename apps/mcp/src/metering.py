"""MCP call metering — tracks per-user per-month call counts.

In-memory implementation suitable for testing.
Production would use Redis or PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timezone

TIER_LIMITS = {
    "free": 50,
    "team": 500,
    "enterprise": None,  # None = unlimited
}


class QuotaExceededError(Exception):
    """User quota exceeded."""

    def __init__(
        self, user_id: str, limit: int | None, current: int
    ) -> None:
        """Initialize quota error.

        Args:
            user_id: User identifier
            limit: Quota limit (None for unlimited)
            current: Current usage count
        """
        self.user_id = user_id
        self.limit = limit
        self.current = current
        if limit is not None:
            message = (
                f"Quota exceeded for user {user_id}: "
                f"{current} >= {limit}"
            )
        else:
            message = f"Unexpected quota error for user {user_id}"
        super().__init__(message)


class MeteringService:
    """Tracks per-user per-month API call counts."""

    def __init__(self) -> None:
        """Initialize metering service with in-memory storage."""
        # Storage: {(user_id, year, month) -> count}
        self._calls: dict[tuple[str, int, int], int] = {}

    def increment(self, user_id: str, tier: str) -> None:
        """Increment call count for a user.

        Args:
            user_id: User identifier
            tier: User tier (free, team, enterprise)
        """
        now = datetime.now(timezone.utc)
        key = (user_id, now.year, now.month)
        self._calls[key] = self._calls.get(key, 0) + 1

    def _increment_internal(
        self, user_id: str, tier: str, months_offset: int = 0
    ) -> None:
        """Internal increment with month offset (for testing).

        Args:
            user_id: User identifier
            tier: User tier
            months_offset: Month offset (negative for past months)
        """
        now = datetime.now(timezone.utc)
        # Simple offset (doesn't handle year boundaries perfectly for tests)
        year = now.year
        month = now.month + months_offset
        if month < 1:
            year -= 1
            month += 12
        key = (user_id, year, month)
        self._calls[key] = self._calls.get(key, 0) + 1

    def get_count(self, user_id: str) -> int:
        """Get current month call count for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of calls this month
        """
        now = datetime.now(timezone.utc)
        key = (user_id, now.year, now.month)
        return self._calls.get(key, 0)

    def quota_ok(self, user_id: str, tier: str) -> bool:
        """Check if user is within quota.

        Args:
            user_id: User identifier
            tier: User tier (free, team, enterprise)

        Returns:
            True if within quota, False otherwise
        """
        limit = TIER_LIMITS.get(tier, 50)
        if limit is None:
            return True  # Enterprise is unlimited

        current = self.get_count(user_id)
        return current < limit
