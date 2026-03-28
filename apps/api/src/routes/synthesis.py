"""
T172: REST API routes for synthesis candidates.

Endpoints:
  GET  /synthesis/candidates           — list (paginated, filterable by status)
  POST /synthesis/candidates/{id}/approve — approve a pending candidate
  POST /synthesis/candidates/{id}/reject  — reject a pending candidate
  POST /synthesis/candidates/{id}/retry   — retry a failed candidate

Access control:
  - All endpoints require Enterprise plan (enforced via require_enterprise())
  - approve/reject/retry require admin or editor role
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from packages.core.src.domain.rules.synthesis_candidate import CandidateStatus
from packages.core.src.domain.rules.synthesis_service import (
    SynthesisCandidateNotFoundError,
    SynthesisService,
    SynthesisTransitionError,
)

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    approved_by: str | None = Field(
        default=None,
        description="User identifier of the approver. Defaults to the authenticated user.",
    )


class CandidateResponse(BaseModel):
    id: str
    anti_pattern_hash: str
    advisory_count: int
    status: str
    failure_count: int
    failure_reason: str | None = None
    rule_id: str | None = None
    created_at: str
    updated_at: str


class CandidateListResponse(BaseModel):
    items: list[CandidateResponse]
    total: int
    page: int
    page_size: int


class ApproveResponse(BaseModel):
    rule_id: str
    candidate_id: str


class MessageResponse(BaseModel):
    message: str
    candidate_id: str


# ---------------------------------------------------------------------------
# Auth/plan dependency helpers (thin wrappers — real impl in middleware)
# ---------------------------------------------------------------------------


def require_enterprise(request: Request) -> None:
    """Raise 403 if the tenant is not on the Enterprise plan."""
    plan = getattr(request.state, "plan", None)
    if plan != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLAN_REQUIRED",
                "message": "Synthesis candidates require an Enterprise plan.",
                "upgrade_url": "/settings/billing",
            },
        )


def require_editor(request: Request) -> None:
    """Raise 403 if the user is not at least an editor."""
    role = getattr(request.state, "role", None)
    if role not in ("admin", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "This action requires editor or admin role.",
            },
        )


def get_tenant_id(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return tenant_id


def get_user_id(request: Request) -> str:
    return getattr(request.state, "user_id", "unknown")


# ---------------------------------------------------------------------------
# Repository port (injected via FastAPI dependency)
# ---------------------------------------------------------------------------


class SynthesisCandidateQueryRepo(Protocol):
    async def list_by_tenant(
        self,
        tenant_id: str,
        status_filter: CandidateStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Any], int]: ...

    async def get(self, candidate_id: str) -> Any | None: ...

    async def create(self, candidate: Any) -> Any: ...

    async def update_status(
        self,
        candidate_id: str,
        status: CandidateStatus,
        failure_reason: str | None = None,
        increment_failure_count: bool = False,
    ) -> None: ...

    async def list_stale_pending(self, older_than_days: int) -> list[Any]: ...


# FastAPI dependency — real binding provided by the app factory
def get_candidate_repo(request: Request) -> SynthesisCandidateQueryRepo:
    repo = getattr(request.app.state, "candidate_repo", None)
    if repo is None:
        raise HTTPException(status_code=500, detail="candidate_repo not configured")
    return repo


def get_rule_repo(request: Request):  # type: ignore[return]
    repo = getattr(request.app.state, "rule_repo", None)
    if repo is None:
        raise HTTPException(status_code=500, detail="rule_repo not configured")
    return repo


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/candidates",
    response_model=CandidateListResponse,
    summary="List synthesis candidates",
)
async def list_candidates(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _enterprise: None = Depends(require_enterprise),
    tenant_id: str = Depends(get_tenant_id),
    repo: SynthesisCandidateQueryRepo = Depends(get_candidate_repo),
) -> CandidateListResponse:
    parsed_status: CandidateStatus | None = None
    if status_filter:
        try:
            parsed_status = CandidateStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status_filter}'. Valid values: {[s.value for s in CandidateStatus]}",
            ) from exc

    items, total = await repo.list_by_tenant(
        tenant_id=tenant_id,
        status_filter=parsed_status,
        page=page,
        page_size=page_size,
    )

    return CandidateListResponse(
        items=[_to_response(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/candidates/{candidate_id}/approve",
    response_model=ApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a pending synthesis candidate",
)
async def approve_candidate(
    candidate_id: str,
    body: ApproveRequest,
    request: Request,
    _enterprise: None = Depends(require_enterprise),
    _editor: None = Depends(require_editor),
    user_id: str = Depends(get_user_id),
    repo: SynthesisCandidateQueryRepo = Depends(get_candidate_repo),
    rule_repo=Depends(get_rule_repo),
) -> ApproveResponse:
    service = SynthesisService(candidate_repo=repo, rule_repo=rule_repo)
    approved_by = body.approved_by or user_id
    try:
        rule_id = await service.approve(candidate_id, approved_by=approved_by)
    except SynthesisCandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        ) from exc
    except SynthesisTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ApproveResponse(rule_id=rule_id, candidate_id=candidate_id)


@router.post(
    "/candidates/{candidate_id}/reject",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a pending synthesis candidate",
)
async def reject_candidate(
    candidate_id: str,
    request: Request,
    _enterprise: None = Depends(require_enterprise),
    _editor: None = Depends(require_editor),
    repo: SynthesisCandidateQueryRepo = Depends(get_candidate_repo),
    rule_repo=Depends(get_rule_repo),
) -> MessageResponse:
    service = SynthesisService(candidate_repo=repo, rule_repo=rule_repo)
    try:
        await service.reject(candidate_id)
    except SynthesisCandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        ) from exc
    except SynthesisTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return MessageResponse(message="Candidate rejected", candidate_id=candidate_id)


@router.post(
    "/candidates/{candidate_id}/retry",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry a failed synthesis candidate",
)
async def retry_candidate(
    candidate_id: str,
    request: Request,
    _enterprise: None = Depends(require_enterprise),
    _editor: None = Depends(require_editor),
    repo: SynthesisCandidateQueryRepo = Depends(get_candidate_repo),
    rule_repo=Depends(get_rule_repo),
) -> MessageResponse:
    service = SynthesisService(candidate_repo=repo, rule_repo=rule_repo)
    try:
        await service.retry(candidate_id)
    except SynthesisCandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        ) from exc
    except SynthesisTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return MessageResponse(message="Candidate queued for retry", candidate_id=candidate_id)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _to_response(candidate: Any) -> CandidateResponse:
    return CandidateResponse(
        id=candidate.id,
        anti_pattern_hash=candidate.anti_pattern_hash,
        advisory_count=candidate.advisory_count,
        status=candidate.status.value
        if hasattr(candidate.status, "value")
        else str(candidate.status),
        failure_count=candidate.failure_count,
        failure_reason=candidate.failure_reason,
        rule_id=getattr(candidate, "rule_id", None),
        created_at=candidate.created_at.isoformat(),
        updated_at=candidate.updated_at.isoformat(),
    )
