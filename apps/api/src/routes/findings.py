"""
T184: False positive reporting endpoint.

POST /findings/{id}/false-positive
  - Requires editor+ role
  - Delegates to FalsePositiveService
  - Returns 200 with updated finding status + count
  - Returns 404 if finding not found
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from apps.api.src.services.false_positive import FalsePositiveService, FindingNotFound

router = APIRouter(prefix="/findings", tags=["findings"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class FalsePositiveResponse(BaseModel):
    finding_id: str
    status: str
    false_positive_count: int
    rule_disabled: bool = False


# ---------------------------------------------------------------------------
# Auth dependency helpers
# ---------------------------------------------------------------------------

def require_editor(request: Request) -> None:
    """Raise 403 if the user is not at least an editor."""
    role = getattr(request.state, "role", None)
    if role not in ("admin", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Editor or admin role required."},
        )


def get_tenant_id(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return tenant_id


def get_user_id(request: Request) -> str:
    return getattr(request.state, "user_id", "unknown")


def get_service(request: Request) -> FalsePositiveService:
    svc = getattr(request.app.state, "false_positive_service", None)
    if svc is None:
        raise HTTPException(status_code=500, detail="false_positive_service not configured")
    return svc


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post(
    "/{finding_id}/false-positive",
    response_model=FalsePositiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Report a finding as a false positive",
)
async def report_false_positive(
    finding_id: str,
    request: Request,
    _editor: None = Depends(require_editor),
    user_id: str = Depends(get_user_id),
    service: FalsePositiveService = Depends(get_service),
) -> FalsePositiveResponse:
    """
    Mark a finding as a false positive.

    - Increments `false_positive_count` on the finding
    - Sets `status = false_positive`
    - Auto-disables the source Semgrep rule when count reaches 3
    """
    try:
        updated = await service.report(finding_id=finding_id, reported_by=user_id)
    except FindingNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found",
        )

    from apps.api.src.services.false_positive import FALSE_POSITIVE_DISABLE_THRESHOLD
    rule_disabled = updated.false_positive_count >= FALSE_POSITIVE_DISABLE_THRESHOLD

    return FalsePositiveResponse(
        finding_id=updated.id,
        status=updated.status,
        false_positive_count=updated.false_positive_count,
        rule_disabled=rule_disabled,
    )
