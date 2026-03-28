"""
T156: Per-tier rate limiting middleware.

Limits per plan (requests/minute + burst):
  Free:       30 req/min | burst 60 req/10s
  Team:      120 req/min | burst 240 req/10s
  Enterprise: 600 req/min | burst 1200 req/10s

Uses an in-process token-bucket / sliding-window counter backed by a simple
dict-based store (swappable for Redis in production via ``get_rate_store``).

Response headers on every request:
  X-RateLimit-Limit     — the per-minute limit for the tenant's plan
  X-RateLimit-Remaining — remaining requests in the current window
  X-RateLimit-Reset     — UTC epoch seconds when the window resets

429 response includes:
  Retry-After — seconds until the window resets
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# ---------------------------------------------------------------------------
# Paths that bypass rate limiting
# ---------------------------------------------------------------------------

_BYPASS_PATHS = frozenset(["/health", "/ready", "/metrics"])


# ---------------------------------------------------------------------------
# Tier limits
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TierLimits:
    requests_per_minute: int
    burst_limit: int          # max in burst_window_seconds
    burst_window_seconds: int = 10
    window_seconds: int = 60

    @classmethod
    def for_plan(cls, plan: str) -> "TierLimits":
        _LIMITS: dict[str, TierLimits] = {
            "free": cls(
                requests_per_minute=30,
                burst_limit=60,
            ),
            "team": cls(
                requests_per_minute=120,
                burst_limit=240,
            ),
            "enterprise": cls(
                requests_per_minute=600,
                burst_limit=1200,
            ),
        }
        return _LIMITS.get(plan, _LIMITS["free"])


# ---------------------------------------------------------------------------
# In-process counter store (replace with Redis adapter in production)
# ---------------------------------------------------------------------------

class _InMemoryRateStore:
    """Sliding-window counter backed by a plain dict.
    Keys are (tenant_key, window_bucket) tuples."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def increment(self, key: str, window: int) -> int:
        bucket = int(time.time() / window)
        full_key = f"{key}:{bucket}"
        self._counts[full_key] = self._counts.get(full_key, 0) + 1
        return self._counts[full_key]

    def get_count(self, key: str, window: int) -> int:
        bucket = int(time.time() / window)
        return self._counts.get(f"{key}:{bucket}", 0)

    def ttl_seconds(self, window: int) -> int:
        """Seconds until the current window expires."""
        bucket = int(time.time() / window)
        return window - int(time.time() % window)


_default_store = _InMemoryRateStore()


def get_rate_store() -> _InMemoryRateStore:
    """Return the active rate limit store. Override in tests."""
    return _default_store


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        super().__init__(app, **kwargs)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Bypass health probes and metrics endpoints
        if any(path.startswith(p) for p in _BYPASS_PATHS):
            return await call_next(request)

        tenant_id: str = getattr(request.state, "tenant_id", "anonymous")
        plan: str = getattr(request.state, "plan", "free")

        limits = TierLimits.for_plan(plan)
        store = get_rate_store()

        minute_key = f"rl:{tenant_id}:minute"
        burst_key = f"rl:{tenant_id}:burst"

        # Check current counts BEFORE incrementing
        current_minute = store.get_count(minute_key, limits.window_seconds)
        current_burst = store.get_count(burst_key, limits.burst_window_seconds)

        # Enforce per-minute limit
        if current_minute >= limits.requests_per_minute:
            retry_after = store.ttl_seconds(limits.window_seconds)
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": f"Rate limit exceeded. Max {limits.requests_per_minute} requests/minute.",
                    "code": "RATE_LIMITED",
                },
            )

        # Enforce burst limit
        if current_burst >= limits.burst_limit:
            retry_after = store.ttl_seconds(limits.burst_window_seconds)
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": f"Burst limit exceeded. Max {limits.burst_limit} requests/{limits.burst_window_seconds}s.",
                    "code": "RATE_LIMITED",
                },
            )

        # Increment counters
        new_minute_count = store.increment(minute_key, limits.window_seconds)
        store.increment(burst_key, limits.burst_window_seconds)

        remaining = max(0, limits.requests_per_minute - new_minute_count)
        reset_at = int(time.time()) + store.ttl_seconds(limits.window_seconds)

        response = await call_next(request)

        # Attach rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limits.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)

        return response
