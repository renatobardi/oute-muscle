"""
T155: RLS middleware — extracts tenant from JWT Bearer token or X-API-Key header,
then sets the PostgreSQL session variable ``app.tenant_id`` via SET LOCAL so that
all RLS policies in the current transaction can filter rows automatically.

Context enrichment written to request.state:
  - tenant_id: str
  - user_id:   str | None
  - plan:      str  ("free" | "team" | "enterprise")
  - role:      str  ("admin" | "editor" | "viewer")
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from apps.api.src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routes that don't require auth (allow-list)
# ---------------------------------------------------------------------------

_PUBLIC_PATHS = frozenset(
    [
        "/health",
        "/ready",
        "/metrics",
        "/v1/tenants/register",
        "/docs",
        "/openapi.json",
    ]
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RLSMiddleware(BaseHTTPMiddleware):
    """
    1. Extract tenant + user from Bearer JWT or X-API-Key.
    2. Populate request.state (tenant_id, user_id, plan, role).
    3. After the request handler acquires a DB session, the session factory
       calls ``apply_tenant_context`` to SET LOCAL the tenant variable.

    The actual SET LOCAL is done in the session context manager
    (packages/db/src/session.py), not here — because middleware cannot
    easily intercept the exact moment a DB connection is checked out.
    This middleware only populates request.state so the session factory
    can read it.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Public paths bypass auth entirely
        if any(path.startswith(p) for p in _PUBLIC_PATHS):
            return await call_next(request)

        # ------------------------------------------------------------------
        # 1. Extract credentials
        # ------------------------------------------------------------------
        tenant_id, user_id, plan, role = None, None, "free", "viewer"

        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]
            result = _decode_jwt(token)
            if result is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid or expired token", "code": "UNAUTHORIZED"},
                )
            tenant_id, user_id, plan, role = result

        elif api_key:
            result = await _resolve_api_key(api_key, request)
            if result is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid API key", "code": "UNAUTHORIZED"},
                )
            tenant_id, user_id, plan, role = result

        else:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "code": "UNAUTHORIZED",
                },
            )

        # ------------------------------------------------------------------
        # 2. Populate request.state
        # ------------------------------------------------------------------
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.plan = plan
        request.state.role = role

        return await call_next(request)


# ---------------------------------------------------------------------------
# JWT decoding
# ---------------------------------------------------------------------------


def _decode_jwt(
    token: str,
) -> tuple[str, str, str, str] | None:
    """
    Decode and validate the JWT.
    Returns (tenant_id, user_id, plan, role) or None on failure.

    Expected claims:
      sub          → user_id
      https://outemuscle.com/tenant_id  → tenant_id
      https://outemuscle.com/plan       → plan
      https://outemuscle.com/role       → role
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.debug("Invalid JWT: %s", exc)
        return None

    tenant_claim = "https://outemuscle.com/tenant_id"
    plan_claim = "https://outemuscle.com/plan"
    role_claim = "https://outemuscle.com/role"

    tenant_id = payload.get(tenant_claim)
    user_id = payload.get("sub")
    plan = payload.get(plan_claim, "free")
    role = payload.get(role_claim, "viewer")

    if not tenant_id or not user_id:
        logger.debug("JWT missing required claims: tenant_id=%s user_id=%s", tenant_id, user_id)
        return None

    return tenant_id, user_id, plan, role


# ---------------------------------------------------------------------------
# API key resolution (delegated to DB lookup)
# ---------------------------------------------------------------------------


async def _resolve_api_key(
    api_key: str,
    request: Request,
) -> tuple[str, str, str, str] | None:
    """
    Look up an API key in the database.
    Returns (tenant_id, user_id, plan, role) or None.

    The actual lookup is performed via the DB session stored in app.state.
    """
    db: AsyncSession | None = getattr(request.app.state, "db_session_factory", None)
    if db is None:
        logger.error("No DB session factory on app.state — cannot resolve API key")
        return None

    async with db() as session:
        result = await session.execute(
            text(
                "SELECT t.id AS tenant_id, t.plan, "
                "       ak.user_id, "
                "       COALESCE(u.role, 'viewer') AS role "
                "FROM api_keys ak "
                "JOIN tenants t ON t.id = ak.tenant_id "
                "LEFT JOIN users u ON u.id = ak.user_id "
                "WHERE ak.key_hash = encode(digest(:key, 'sha256'), 'hex') "
                "  AND ak.revoked_at IS NULL"
            ),
            {"key": api_key},
        )
        row = result.fetchone()

    if row is None:
        return None

    return row.tenant_id, row.user_id, row.plan, row.role


# ---------------------------------------------------------------------------
# Session-level helper — called by the DB session factory
# ---------------------------------------------------------------------------


async def apply_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Issue SET LOCAL "app.tenant_id" = <tenant_id> on the current connection.
    Must be called inside an open transaction (SET LOCAL is transaction-scoped).
    """
    await session.execute(
        text('SET LOCAL "app.tenant_id" = :tenant_id'),
        {"tenant_id": tenant_id},
    )
