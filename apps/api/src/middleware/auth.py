"""API key authentication middleware for REST API (Phase 8, T129).

Validates X-API-Key header and resolves tenant information.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

# In-memory key store (Phase 8 stub — will be replaced by DB lookup in Phase 10)
_API_KEY_STORE: dict[str, dict[str, str]] = {}


def register_api_key(key: str, tenant_id: str, tier: str) -> None:
    """Register an API key (used by tests and seed scripts).

    Args:
        key: API key string
        tenant_id: Tenant identifier
        tier: Tier level (free, team, enterprise)
    """
    _API_KEY_STORE[key] = {"tenant_id": tenant_id, "tier": tier}


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> dict[str, str]:
    """FastAPI dependency: validates X-API-Key header, returns tenant dict.

    Args:
        request: FastAPI Request object
        x_api_key: X-API-Key header value

    Returns:
        dict with keys: tenant_id, tier

    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    tenant = _API_KEY_STORE.get(x_api_key)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return tenant
