"""REST API routes for incidents (T081-T083).

Endpoints:
    POST /incidents — Create incident
    GET /incidents — List incidents (with pagination)
    GET /incidents/:id — Get incident by ID
    PUT /incidents/:id — Update incident (optimistic locking)
    DELETE /incidents/:id — Soft-delete incident
    POST /incidents/ingest-url — Ingest from URL (draft)
    GET /incidents?q=&semantic=true — Search incidents
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

# Request/Response schemas (Pydantic v2)


class IncidentCreateRequest(BaseModel):
    """Request body for POST /incidents."""

    title: str = Field(..., min_length=1, max_length=500)
    category: str = Field(...)  # unsafe-regex, etc.
    severity: str = Field(...)  # critical, high, medium, low
    anti_pattern: str = Field(..., min_length=1)
    remediation: str = Field(..., min_length=1)
    date: dt.date | None = None
    organization: str | None = Field(None, max_length=255)
    source_url: str | None = Field(None, max_length=2048)
    affected_languages: list[str] = Field(default_factory=list)
    code_example: str | None = None
    tags: list[str] = Field(default_factory=list)
    static_rule_possible: bool = False
    semgrep_rule_id: str | None = Field(None, max_length=50)


class IncidentUpdateRequest(BaseModel):
    """Request body for PUT /incidents/:id (optimistic locking)."""

    version: int = Field(..., ge=1)  # Expected version in DB
    title: str | None = Field(None, min_length=1, max_length=500)
    category: str | None = None
    severity: str | None = None
    anti_pattern: str | None = Field(None, min_length=1)
    remediation: str | None = Field(None, min_length=1)
    date: dt.date | None = None
    organization: str | None = Field(None, max_length=255)
    affected_languages: list[str] | None = None
    code_example: str | None = None
    tags: list[str] | None = None
    static_rule_possible: bool | None = None
    semgrep_rule_id: str | None = Field(None, max_length=50)


class IncidentResponse(BaseModel):
    """Response body for incident endpoints (no embedding)."""

    id: str
    tenant_id: str | None
    title: str
    category: str
    severity: str
    anti_pattern: str
    remediation: str
    date: dt.date | None
    organization: str | None
    source_url: str | None
    affected_languages: list[str]
    code_example: str | None
    tags: list[str]
    static_rule_possible: bool
    semgrep_rule_id: str | None
    version: int
    deleted_at: dt.datetime | None
    created_by: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    """Response body for GET /incidents (with pagination)."""

    items: list[IncidentResponse]
    total: int
    page: int
    per_page: int


class IncidentIngestRequest(BaseModel):
    """Request body for POST /incidents/ingest-url."""

    url: str


class IncidentIngestResponse(BaseModel):
    """Response body for POST /incidents/ingest-url."""

    draft: IncidentResponse


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    code: str
    details: dict = {}


# Router setup

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(request: IncidentCreateRequest) -> IncidentResponse:
    """Create a new incident.

    POST /incidents
    {
        "title": "...",
        "category": "unsafe-regex",
        "severity": "critical",
        ...
    }

    Returns:
        201 Created: Incident object
    """
    raise NotImplementedError("Adapter implementation pending")


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    q: str | None = Query(None, description="Keyword search"),
    semantic: bool = Query(False, description="Use semantic search"),
    category: str | None = Query(None, description="Filter by category"),
    severity: str | None = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
) -> IncidentListResponse:
    """List incidents with optional filtering.

    GET /incidents?q=regex&category=unsafe-regex&page=1&per_page=50
    GET /incidents?q=backtracking&semantic=true

    Query params:
        q: Keyword or semantic search query
        semantic: If true, use embedding-based similarity search
        category: Filter by category
        severity: Filter by severity
        page: Page number (1-indexed)
        per_page: Items per page (1-100)

    Returns:
        200 OK: Paginated incident list
    """
    raise NotImplementedError("Adapter implementation pending")


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str) -> IncidentResponse:
    """Get incident by ID.

    GET /incidents/{incident_id}

    Returns:
        200 OK: Incident object
        404 Not Found: Incident doesn't exist
    """
    raise NotImplementedError("Adapter implementation pending")


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(incident_id: str, request: IncidentUpdateRequest) -> IncidentResponse:
    """Update incident (optimistic locking).

    PUT /incidents/{incident_id}
    {
        "version": 1,
        "title": "Updated title",
        ...
    }

    Returns:
        200 OK: Updated incident
        404 Not Found: Incident doesn't exist
        409 Conflict: Version mismatch (OptimisticLockError)
    """
    raise NotImplementedError("Adapter implementation pending")


@router.delete("/{incident_id}", status_code=204)
async def delete_incident(incident_id: str) -> None:
    """Soft-delete incident.

    DELETE /incidents/{incident_id}

    Returns:
        204 No Content: Deletion successful
        404 Not Found: Incident doesn't exist
        409 Conflict: Incident has active semgrep_rule_id
    """
    raise NotImplementedError("Adapter implementation pending")


@router.post("/ingest-url", response_model=IncidentIngestResponse)
async def ingest_url(request: IncidentIngestRequest) -> IncidentIngestResponse:
    """Ingest incident from URL (LLM extraction draft).

    POST /incidents/ingest-url
    {"url": "https://..."}

    Uses LLM to extract incident metadata from HTML.

    Returns:
        200 OK: Draft incident for review
        409 Conflict: URL already ingested
    """
    raise NotImplementedError("Adapter implementation pending")
