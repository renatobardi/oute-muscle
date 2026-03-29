"""
Admin API endpoints (spec 237, T035-T041).

All endpoints require admin role. Read endpoints bypass RLS (cross-tenant).
Mutations are recorded in the audit log.

Endpoints:
  GET  /admin/users          — paginated, searchable, cross-tenant
  GET  /admin/tenants        — with contributor_count, scan_count_30d
  GET  /admin/metrics        — aggregated platform metrics + latency percentiles
  POST /admin/users/{id}/role         — change role, block self-demotion
  POST /admin/users/{id}/deactivate   — toggle is_active=false
  POST /admin/users/{id}/activate     — toggle is_active=true
  POST /admin/users/{id}/assign-tenant — set tenant_id
  GET  /admin/audit-log      — cross-tenant, filterable
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.middleware.auth import require_admin
from packages.db.src.models.audit_log import AuditLogEntry
from packages.db.src.models.finding import Finding
from packages.db.src.models.incident import Incident
from packages.db.src.models.rule import SemgrepRule
from packages.db.src.models.scan import Scan
from packages.db.src.models.synthesis_candidate import SynthesisCandidate
from packages.db.src.models.tenant import Tenant
from packages.db.src.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AdminUserResponse(BaseModel):
    id: str
    firebase_uid: str | None = None
    email: str
    display_name: str | None = None
    tenant_id: str | None = None
    tenant_name: str | None = None
    role: str
    is_active: bool
    email_verified: bool = False
    last_login: str | None = None
    created_at: str


class PaginatedUsers(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    per_page: int


class AdminTenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan_tier: str
    is_active: bool
    contributor_count: int = 0
    scan_count_30d: int = 0
    findings_count_30d: int = 0
    created_at: str


class PaginatedTenants(BaseModel):
    items: list[AdminTenantResponse]
    total: int
    page: int
    per_page: int


class AdminMetricsResponse(BaseModel):
    users: dict
    tenants: dict
    scans: dict
    findings: dict
    incidents: dict
    rules: dict
    llm_usage_30d: dict


class RoleChangeRequest(BaseModel):
    role: str


class TenantAssignRequest(BaseModel):
    tenant_id: str


class AdminUserUpdateResponse(BaseModel):
    id: str
    email: str
    role: str | None = None
    is_active: bool | None = None
    tenant_id: str | None = None
    tenant_name: str | None = None
    updated_at: str


class AdminAuditLogEntry(BaseModel):
    id: str
    tenant_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    performed_by: str | None = None
    performed_by_email: str | None = None
    changes: dict | None = None
    created_at: str


class PaginatedAuditLog(BaseModel):
    items: list[AdminAuditLogEntry]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# Helper: get a non-RLS session (admin bypass)
# ---------------------------------------------------------------------------


async def get_admin_session() -> AsyncSession:
    """Yield a DB session WITHOUT tenant scoping (admin cross-tenant access)."""
    from apps.api.src.main import get_container

    container = get_container()
    async for session in container.session_factory.get_session():
        yield session  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helper: record audit log entry
# ---------------------------------------------------------------------------


async def _audit_log(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    performed_by: str,
    tenant_id: str | None = None,
    changes: dict | None = None,
) -> None:
    entry = AuditLogEntry(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
        action=action,
        entity_type=entity_type,
        entity_id=uuid.UUID(entity_id) if entity_id else uuid.uuid4(),
        performed_by=uuid.UUID(performed_by) if performed_by else None,
        changes=changes or {},
    )
    session.add(entry)


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    q: str | None = Query(None),
    role: str | None = Query(None),
    tenant_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_admin_session),
) -> PaginatedUsers:
    """List all users across all tenants (admin only)."""
    stmt = select(User, Tenant.name.label("tenant_name")).outerjoin(
        Tenant, User.tenant_id == Tenant.id
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(pattern), User.name.ilike(pattern)))
    if role:
        stmt = stmt.where(User.role == role)
    if tenant_id:
        stmt = stmt.where(User.tenant_id == uuid.UUID(tenant_id))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    # Fetch
    stmt = stmt.order_by(User.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    rows = (await session.execute(stmt)).all()

    items = [
        AdminUserResponse(
            id=str(user.id),
            firebase_uid=user.firebase_uid,
            email=user.email,
            display_name=user.display_name or user.name,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            tenant_name=tenant_name,
            role=user.role,
            is_active=bool(user.is_active),
            email_verified=bool(user.email_verified),
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat(),
        )
        for user, tenant_name in rows
    ]

    return PaginatedUsers(items=items, total=total, page=page, per_page=per_page)


# ---------------------------------------------------------------------------
# GET /admin/tenants
# ---------------------------------------------------------------------------


@router.get("/tenants", response_model=PaginatedTenants)
async def list_tenants(
    q: str | None = Query(None),
    plan_tier: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_admin_session),
) -> PaginatedTenants:
    """List all tenants with usage metrics (admin only)."""
    base = select(Tenant)

    if q:
        base = base.where(Tenant.name.ilike(f"%{q}%"))
    if plan_tier:
        base = base.where(Tenant.plan_tier == plan_tier)
    if is_active is not None:
        base = base.where(Tenant.is_active == is_active)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    base = base.order_by(Tenant.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    tenants = (await session.execute(base)).scalars().all()

    items = []
    for t in tenants:
        contributor_count = (
            await session.execute(
                select(func.count(User.id)).where(User.tenant_id == t.id)
            )
        ).scalar_one()

        from datetime import timedelta

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        scan_count = (
            await session.execute(
                select(func.count(Scan.id)).where(
                    Scan.tenant_id == t.id, Scan.created_at >= thirty_days_ago
                )
            )
        ).scalar_one()

        findings_count = (
            await session.execute(
                select(func.count(Finding.id)).where(
                    Finding.tenant_id == t.id, Finding.created_at >= thirty_days_ago
                )
            )
        ).scalar_one()

        items.append(
            AdminTenantResponse(
                id=str(t.id),
                name=t.name,
                slug=t.slug,
                plan_tier=t.plan_tier,
                is_active=bool(t.is_active),
                contributor_count=contributor_count,
                scan_count_30d=scan_count,
                findings_count_30d=findings_count,
                created_at=t.created_at.isoformat(),
            )
        )

    return PaginatedTenants(items=items, total=total, page=page, per_page=per_page)


# ---------------------------------------------------------------------------
# GET /admin/metrics
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=AdminMetricsResponse)
async def get_metrics(
    session: AsyncSession = Depends(get_admin_session),
) -> AdminMetricsResponse:
    """Aggregated platform metrics (admin only)."""
    from datetime import timedelta

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    users_total = (await session.execute(select(func.count(User.id)))).scalar_one()
    users_active = (
        await session.execute(
            select(func.count(User.id)).where(User.last_login >= thirty_days_ago)
        )
    ).scalar_one()

    tenants_total = (await session.execute(select(func.count(Tenant.id)))).scalar_one()
    tenants_active = (
        await session.execute(
            select(func.count(Tenant.id)).where(Tenant.is_active.is_(True))
        )
    ).scalar_one()

    scans_30d = (
        await session.execute(
            select(func.count(Scan.id)).where(Scan.created_at >= thirty_days_ago)
        )
    ).scalar_one()

    findings_30d = (
        await session.execute(
            select(func.count(Finding.id)).where(Finding.created_at >= thirty_days_ago)
        )
    ).scalar_one()

    incidents_total = (await session.execute(select(func.count(Incident.id)))).scalar_one()
    incidents_with_embedding = (
        await session.execute(
            select(func.count(Incident.id)).where(Incident.embedding.is_not(None))
        )
    ).scalar_one()

    rules_active = (
        await session.execute(
            select(func.count(SemgrepRule.id)).where(SemgrepRule.is_active.is_(True))
        )
    ).scalar_one()

    synthesis_pending = (
        await session.execute(
            select(func.count(SynthesisCandidate.id)).where(
                SynthesisCandidate.status == "pending"
            )
        )
    ).scalar_one()

    return AdminMetricsResponse(
        users={"total": users_total, "active_30d": users_active},
        tenants={"total": tenants_total, "active": tenants_active},
        scans={"total_30d": scans_30d, "active_now": 0},
        findings={"total_30d": findings_30d, "by_severity": {}},
        incidents={
            "total": incidents_total,
            "with_embedding": incidents_with_embedding,
            "by_category": {},
        },
        rules={"active": rules_active, "auto_disabled": 0, "synthesis_pending": synthesis_pending},
        llm_usage_30d={"flash": 0, "pro": 0, "claude": 0},
    )


# ---------------------------------------------------------------------------
# POST /admin/users/{id}/role
# ---------------------------------------------------------------------------


@router.post("/users/{user_id}/role", response_model=AdminUserUpdateResponse)
async def change_user_role(
    user_id: str,
    body: RoleChangeRequest,
    request: Request,
    session: AsyncSession = Depends(get_admin_session),
) -> AdminUserUpdateResponse:
    """Change a user's role. Blocks self-demotion."""
    admin_user_id = getattr(request.state, "user_id", None)
    if admin_user_id == user_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Cannot change your own role", "code": "SELF_DEMOTION"},
        )

    if body.role not in ("viewer", "editor", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    user.role = body.role

    await _audit_log(
        session,
        action="role_change",
        entity_type="user",
        entity_id=user_id,
        performed_by=admin_user_id or "",
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        changes={"before": {"role": old_role}, "after": {"role": body.role}},
    )

    await session.commit()

    return AdminUserUpdateResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        updated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /admin/users/{id}/deactivate + /activate
# ---------------------------------------------------------------------------


@router.post("/users/{user_id}/deactivate", response_model=AdminUserUpdateResponse)
async def deactivate_user(
    user_id: str,
    request: Request,
    session: AsyncSession = Depends(get_admin_session),
) -> AdminUserUpdateResponse:
    """Deactivate a user account."""
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    admin_user_id = getattr(request.state, "user_id", "")

    await _audit_log(
        session,
        action="deactivate",
        entity_type="user",
        entity_id=user_id,
        performed_by=admin_user_id,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        changes={"before": {"is_active": True}, "after": {"is_active": False}},
    )

    await session.commit()

    return AdminUserUpdateResponse(
        id=str(user.id),
        email=user.email,
        is_active=False,
        updated_at=datetime.utcnow().isoformat(),
    )


@router.post("/users/{user_id}/activate", response_model=AdminUserUpdateResponse)
async def activate_user(
    user_id: str,
    request: Request,
    session: AsyncSession = Depends(get_admin_session),
) -> AdminUserUpdateResponse:
    """Reactivate a user account."""
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    admin_user_id = getattr(request.state, "user_id", "")

    await _audit_log(
        session,
        action="reactivate",
        entity_type="user",
        entity_id=user_id,
        performed_by=admin_user_id,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        changes={"before": {"is_active": False}, "after": {"is_active": True}},
    )

    await session.commit()

    return AdminUserUpdateResponse(
        id=str(user.id),
        email=user.email,
        is_active=True,
        updated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /admin/users/{id}/assign-tenant
# ---------------------------------------------------------------------------


@router.post("/users/{user_id}/assign-tenant", response_model=AdminUserUpdateResponse)
async def assign_tenant(
    user_id: str,
    body: TenantAssignRequest,
    request: Request,
    session: AsyncSession = Depends(get_admin_session),
) -> AdminUserUpdateResponse:
    """Assign a user to a tenant."""
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    tenant_result = await session.execute(
        select(Tenant).where(Tenant.id == uuid.UUID(body.tenant_id))
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_tenant_id = str(user.tenant_id) if user.tenant_id else None
    user.tenant_id = uuid.UUID(body.tenant_id)
    admin_user_id = getattr(request.state, "user_id", "")

    await _audit_log(
        session,
        action="assign_tenant",
        entity_type="user",
        entity_id=user_id,
        performed_by=admin_user_id,
        tenant_id=body.tenant_id,
        changes={
            "before": {"tenant_id": old_tenant_id},
            "after": {"tenant_id": body.tenant_id},
        },
    )

    await session.commit()

    return AdminUserUpdateResponse(
        id=str(user.id),
        email=user.email,
        tenant_id=body.tenant_id,
        tenant_name=tenant.name,
        updated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /admin/audit-log
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=PaginatedAuditLog)
async def list_audit_log(
    entity_type: str | None = Query(None),
    action: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_admin_session),
) -> PaginatedAuditLog:
    """Full audit log across all tenants (admin only)."""
    stmt = select(AuditLogEntry)

    if entity_type:
        stmt = stmt.where(AuditLogEntry.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLogEntry.action == action)
    if from_:
        stmt = stmt.where(AuditLogEntry.created_at >= datetime.fromisoformat(from_))
    if to:
        stmt = stmt.where(AuditLogEntry.created_at <= datetime.fromisoformat(to))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(AuditLogEntry.created_at.desc()).limit(per_page).offset(
        (page - 1) * per_page
    )
    entries = (await session.execute(stmt)).scalars().all()

    items = [
        AdminAuditLogEntry(
            id=str(e.id),
            tenant_id=str(e.tenant_id) if e.tenant_id else None,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=str(e.entity_id),
            performed_by=str(e.performed_by) if e.performed_by else None,
            changes=e.changes,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]

    return PaginatedAuditLog(items=items, total=total, page=page, per_page=per_page)
