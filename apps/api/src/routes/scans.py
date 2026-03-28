"""REST API routes for scan management (Phase 5, T098).

Endpoints:
    POST /scans — Trigger a new scan (L1, L2, or both)
    GET /scans/{scan_id} — Get scan status and results
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Request/Response schemas


class ScanCreateRequest(BaseModel):
    """Request body for POST /scans."""

    repo_url: str = Field(..., min_length=1, max_length=2048, description="Repository URL")
    pr_number: int = Field(..., ge=1, description="Pull request number")
    tenant_id: str = Field(..., min_length=1, description="Tenant UUID")
    layer: str = Field("both", description="Scan layer: 'L1' | 'L2' | 'both'")


class FindingResponse(BaseModel):
    """Single Layer 1 finding."""

    id: str
    file_path: str
    start_line: int
    end_line: int
    severity: str
    message: str
    remediation: str


class AdvisoryResponse(BaseModel):
    """Single Layer 2 advisory."""

    id: str
    confidence_score: float
    risk_level: str
    analysis_text: str
    llm_model_used: str
    matched_anti_pattern: str


class ScanCreateResponse(BaseModel):
    """Response body for POST /scans."""

    scan_id: str = Field(..., description="Unique scan identifier")
    status: str = Field(..., description="Scan status: 'queued'|'running'|'completed'|'failed'")
    created_at: datetime


class ScanStatusResponse(BaseModel):
    """Response body for GET /scans/{scan_id}."""

    scan_id: str
    status: str  # running, completed, failed, timeout
    risk_level: str | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    advisory: AdvisoryResponse | None = None
    created_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None


# Router setup

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanCreateResponse, status_code=202)
async def create_scan(request: ScanCreateRequest) -> ScanCreateResponse:
    """Trigger a new code scan (Layer 1, Layer 2, or both).

    POST /scans
    {
        "repo_url": "https://github.com/org/repo",
        "pr_number": 123,
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "layer": "both"
    }

    Layer selection:
        L1 — Run Semgrep rules synchronously, return findings immediately
        L2 — Queue RAG worker job (async), return scan_id to poll
        both — Run L1 sync, queue L2 async

    Returns:
        202 Accepted: Scan queued for processing
        Scan status can be checked via GET /scans/{scan_id}
    """
    raise NotImplementedError(
        "Scan creation adapter implementation pending (Phase 5)"
    )


@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str) -> ScanStatusResponse:
    """Get scan status and results.

    GET /scans/{scan_id}

    Response structure:
        - scan_id: Unique identifier
        - status: Current lifecycle status
        - risk_level: Computed from Layer 1 findings (if L1 complete)
        - findings: Array of Layer 1 matches (if L1 complete)
        - advisory: Layer 2 RAG advisory (if L2 complete)
        - created_at: Scan initiation timestamp
        - completed_at: Scan completion timestamp (if done)
        - duration_ms: Total execution time (if done)

    Status codes:
        200 OK: Scan found (any status)
        404 Not Found: Scan doesn't exist
    """
    raise NotImplementedError(
        "Scan status retrieval adapter implementation pending (Phase 5)"
    )
