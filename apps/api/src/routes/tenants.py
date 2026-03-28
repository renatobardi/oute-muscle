"""
T159: REST API routes for tenant management.

  GET  /tenants/me               — current tenant profile + usage
  GET  /tenants/me/users         — list tenant members
  POST /tenants/me/users/invite  — invite a user (admin only)
  PATCH /tenants/me/users/{id}   — update user role (admin only)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.src.domain.tenants.plan_limits import (
    Plan,
    PlanLimitError,
    PlanLimits,
)
from packages.db.src.session import get_session

router = APIRouter(prefix="/tenants", tags=["tenants"])


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------


class TenantResponse(BaseModel):
    id: str
    name: str
    plan: str
    contributor_count: int
    repo_count: int
    created_at: str


class TenantUserResponse(BaseModel):
    id: str
    email: str
    role: str
    joined_at: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "editor"


class UpdateRoleRequest(BaseModel):
    role: str


# ---------------------------------------------------------------------------
# Dependency: current tenant from request.state
# ---------------------------------------------------------------------------


def get_tenant_id(request: Request) -> str:
    return request.state.tenant_id


def require_admin(request: Request) -> None:
    if getattr(request.state, "role", None) != "admin":
        raise HTTPException(
            status_code=403, detail={"error": "Admin role required", "code": "FORBIDDEN"}
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/me", response_model=TenantResponse)
async def get_current_tenant(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    result = await session.execute(
        text(
            "SELECT id, name, plan, created_at, "
            "  (SELECT COUNT(*) FROM users WHERE tenant_id = t.id) AS contributor_count, "
            "  (SELECT COUNT(DISTINCT repository) FROM scans WHERE tenant_id = t.id) AS repo_count "
            "FROM tenants t "
            "WHERE t.id = :tid"
        ),
        {"tid": tenant_id},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404, detail={"error": "Tenant not found", "code": "NOT_FOUND"}
        )

    return TenantResponse(
        id=row.id,
        name=row.name,
        plan=row.plan,
        contributor_count=row.contributor_count,
        repo_count=row.repo_count,
        created_at=row.created_at.isoformat(),
    )


@router.get("/me/users", response_model=list[TenantUserResponse])
async def list_tenant_users(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[TenantUserResponse]:
    result = await session.execute(
        text(
            "SELECT id, email, role, created_at AS joined_at "
            "FROM users "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "ORDER BY created_at"
        ),
        {"tid": tenant_id},
    )
    return [
        TenantUserResponse(
            id=row.id,
            email=row.email,
            role=row.role,
            joined_at=row.joined_at.isoformat(),
        )
        for row in result.fetchall()
    ]


@router.post(
    "/me/users/invite",
    status_code=status.HTTP_201_CREATED,
)
async def invite_user(
    body: InviteRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    require_admin(request)

    # Check role is valid
    if body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(
            status_code=422,
            detail={"error": "Invalid role", "code": "VALIDATION_ERROR"},
        )

    # Check contributor limit
    count_result = await session.execute(
        text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tenant_id},
    )
    current_count: int = count_result.scalar_one()

    # Get tenant plan
    plan_result = await session.execute(
        text("SELECT plan FROM tenants WHERE id = :tid"),
        {"tid": tenant_id},
    )
    plan_row = plan_result.fetchone()
    plan = Plan.from_str(plan_row.plan if plan_row else "free")

    try:
        PlanLimits.check_contributor_limit(plan, current_count)
    except PlanLimitError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": str(exc), "code": exc.code},
        ) from exc

    # Check for duplicate email
    existing = await session.execute(
        text(
            "SELECT id FROM users WHERE tenant_id = :tid AND email = :email AND deleted_at IS NULL"
        ),
        {"tid": tenant_id, "email": body.email},
    )
    if existing.fetchone():
        raise HTTPException(
            status_code=409,
            detail={"error": "User already exists in tenant", "code": "CONFLICT"},
        )

    # Create the user record (in production this would also send an invitation email)
    user_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO users (id, tenant_id, email, role, created_at, updated_at) "
            "VALUES (:id, :tid, :email, :role, NOW(), NOW())"
        ),
        {"id": user_id, "tid": tenant_id, "email": body.email, "role": body.role},
    )

    return {"message": "Invitation sent", "user_id": user_id}


@router.patch("/me/users/{user_id}")
async def update_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> TenantUserResponse:
    require_admin(request)

    if body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(
            status_code=422,
            detail={"error": "Invalid role", "code": "VALIDATION_ERROR"},
        )

    result = await session.execute(
        text(
            "UPDATE users SET role = :role, updated_at = NOW() "
            "WHERE id = :uid AND tenant_id = :tid AND deleted_at IS NULL "
            "RETURNING id, email, role, created_at"
        ),
        {"role": body.role, "uid": user_id, "tid": tenant_id},
    )
    row = result.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "User not found", "code": "NOT_FOUND"},
        )

    return TenantUserResponse(
        id=row.id,
        email=row.email,
        role=row.role,
        joined_at=row.created_at.isoformat(),
    )
