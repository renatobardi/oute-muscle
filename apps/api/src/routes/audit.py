"""
T160: REST API route for audit log (Enterprise only).

  GET /audit-log  — paginated list of audit log entries.

Query params: entity_type, action, from, to, page (default 1), per_page (default 50, max 200).
Requires Enterprise plan; returns 403 for Free/Team tenants.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.src.domain.tenants.plan_limits import Plan
from packages.db.src.session import get_session

router = APIRouter(prefix="/audit-log", tags=["audit"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class AuditLogEntryResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    actor_email: str
    before: dict | None = None
    after: dict | None = None
    created_at: str


class PaginatedAuditLog(BaseModel):
    items: list[AuditLogEntryResponse]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_tenant_id(request: Request) -> str:
    return request.state.tenant_id


def require_enterprise(request: Request) -> None:
    plan = getattr(request.state, "plan", "free")
    if plan != Plan.ENTERPRISE.value:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Audit log is available on the Enterprise plan only.",
                "code": "PLAN_LIMIT_EXCEEDED",
            },
        )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedAuditLog)
async def list_audit_log(
    request: Request,
    entity_type: str | None = Query(None),
    action: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> PaginatedAuditLog:
    require_enterprise(request)

    # Build WHERE clauses dynamically
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": per_page, "offset": (page - 1) * per_page}

    if entity_type:
        conditions.append("entity_type = :entity_type")
        params["entity_type"] = entity_type

    if action:
        conditions.append("action = :action")
        params["action"] = action

    if from_:
        conditions.append("created_at >= :from_dt")
        params["from_dt"] = datetime.fromisoformat(from_)

    if to:
        conditions.append("created_at <= :to_dt")
        params["to_dt"] = datetime.fromisoformat(to)

    where = " AND ".join(conditions)

    # Count
    count_result = await session.execute(
        text(f"SELECT COUNT(*) FROM audit_log_entries WHERE {where}"),
        params,
    )
    total: int = count_result.scalar_one()

    # Fetch
    rows_result = await session.execute(
        text(
            f"SELECT id, entity_type, entity_id, action, actor_id, actor_email, "
            f"       before_data, after_data, created_at "
            f"FROM audit_log_entries "
            f"WHERE {where} "
            f"ORDER BY created_at DESC "
            f"LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    items = [
        AuditLogEntryResponse(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            actor_id=row.actor_id,
            actor_email=row.actor_email,
            before=row.before_data,
            after=row.after_data,
            created_at=row.created_at.isoformat(),
        )
        for row in rows_result.fetchall()
    ]

    return PaginatedAuditLog(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
