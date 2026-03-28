"""REST API routes for incidents (T081-T083).

Endpoints:
    POST   /incidents          — Create incident
    GET    /incidents          — List incidents (pagination + filters)
    GET    /incidents/{id}     — Get incident by ID
    PUT    /incidents/{id}     — Update incident (optimistic locking)
    DELETE /incidents/{id}     — Soft-delete incident
    POST   /incidents/ingest-url — Ingest from URL (LLM extraction draft)
    GET    /incidents?q=&semantic=true — Keyword or semantic search
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from apps.api.src.dependencies import get_incident_service
from packages.core.src.domain.incidents.entity import Incident
from packages.core.src.domain.incidents.enums import IncidentCategory, IncidentSeverity
from packages.core.src.domain.incidents.service import IncidentService
from packages.core.src.ports.incident_repo import (
    DuplicateSourceUrlError,
    IncidentHasActiveRuleError,
    OptimisticLockError,
)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    category: IncidentCategory
    severity: IncidentSeverity
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
    version: int = Field(..., ge=1, description="Expected current version (optimistic locking)")
    title: str | None = Field(None, min_length=1, max_length=500)
    category: IncidentCategory | None = None
    severity: IncidentSeverity | None = None
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

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, incident: Incident) -> "IncidentResponse":
        return cls(
            id=str(incident.id),
            tenant_id=str(incident.tenant_id) if incident.tenant_id else None,
            title=incident.title,
            category=str(incident.category.value),
            severity=str(incident.severity.value),
            anti_pattern=incident.anti_pattern,
            remediation=incident.remediation,
            date=incident.date,
            organization=incident.organization,
            source_url=incident.source_url,
            affected_languages=incident.affected_languages,
            code_example=incident.code_example,
            tags=incident.tags,
            static_rule_possible=incident.static_rule_possible,
            semgrep_rule_id=incident.semgrep_rule_id,
            version=incident.version,
            deleted_at=incident.deleted_at,
            created_by=str(incident.created_by) if incident.created_by else None,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        )


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    page: int
    per_page: int


class IncidentIngestRequest(BaseModel):
    url: str


class IncidentIngestResponse(BaseModel):
    draft: IncidentResponse


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/incidents", tags=["incidents"])

IncidentSvc = Annotated[IncidentService, Depends(get_incident_service)]


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    request: IncidentCreateRequest,
    service: IncidentSvc,
) -> IncidentResponse:
    """Create a new incident in the knowledge base.

    Automatically generates a 768-dim embedding (if GCP is configured)
    for semantic search. Rejects duplicate source_url.
    """
    incident = Incident(
        title=request.title,
        category=request.category,
        severity=request.severity,
        anti_pattern=request.anti_pattern,
        remediation=request.remediation,
        date=request.date,
        organization=request.organization,
        source_url=request.source_url,
        affected_languages=request.affected_languages,
        code_example=request.code_example,
        tags=request.tags,
        static_rule_possible=request.static_rule_possible,
        semgrep_rule_id=request.semgrep_rule_id,
        created_by=SYSTEM_USER_ID,  # TODO: replace with auth.current_user.id
    )

    try:
        created = await service.create_incident(incident)
    except DuplicateSourceUrlError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    return IncidentResponse.from_entity(created)


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    service: IncidentSvc,
    q: str | None = Query(None, description="Keyword or semantic search query"),
    semantic: bool = Query(False, description="Use embedding-based semantic search"),
    category: IncidentCategory | None = Query(None),
    severity: IncidentSeverity | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> IncidentListResponse:
    """List incidents with optional filtering and pagination.

    When q + semantic=true: embedding-based similarity search.
    When q only: ILIKE full-text search on title/anti_pattern/remediation.
    Without q: paginated list with category/severity filters.
    """
    offset = (page - 1) * per_page

    if q:
        items = await service.search_incidents(
            q,
            limit=per_page,
            use_semantic=semantic,
        )
        return IncidentListResponse(
            items=[IncidentResponse.from_entity(i) for i in items],
            total=len(items),
            page=page,
            per_page=per_page,
        )

    items = await service.list_incidents(
        category=category,
        severity=severity,
        limit=per_page,
        offset=offset,
    )

    # Count total for pagination
    # For now, use len(items) as approximation — a separate count query can be added later
    # when we expose the repo count() method through the service
    return IncidentListResponse(
        items=[IncidentResponse.from_entity(i) for i in items],
        total=len(items) + offset,  # Approximate: actual count requires extra query
        page=page,
        per_page=per_page,
    )


@router.get("/ingest-url", response_model=IncidentIngestResponse)
async def ingest_url(
    url: str = Query(..., description="URL of the post-mortem to ingest"),
    service: IncidentSvc = None,  # type: ignore[assignment]
) -> IncidentIngestResponse:
    """Preview incident extraction from a URL (LLM draft — not yet saved).

    Fetches the URL content and uses Gemini Flash to extract incident metadata.
    Returns a draft for user review. The draft is NOT persisted until
    the user calls POST /incidents with the confirmed data.
    """
    # TODO: Implement URL fetching + LLM extraction
    # For now, return a minimal draft structure
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="URL ingestion requires LLM extraction — coming in next iteration",
    )


@router.post("/ingest-url", response_model=IncidentIngestResponse)
async def ingest_url_post(
    request: IncidentIngestRequest,
    service: IncidentSvc,
) -> IncidentIngestResponse:
    """Ingest incident from URL (LLM extraction draft).

    POST /incidents/ingest-url
    {"url": "https://...post-mortem..."}

    Fetches HTML, uses Gemini Flash to extract incident fields.
    Returns a draft for review. Not persisted until confirmed.
    """
    # TODO: Implement URL fetching + LLM extraction pipeline
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="URL ingestion requires LLM extraction — coming in next iteration",
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    service: IncidentSvc,
) -> IncidentResponse:
    """Get a single incident by ID.

    Returns 404 if not found or soft-deleted.
    """
    try:
        iid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid incident ID format: {incident_id}",
        )

    incident = await service.incident_repo.get_by_id(iid)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    return IncidentResponse.from_entity(incident)


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    request: IncidentUpdateRequest,
    service: IncidentSvc,
) -> IncidentResponse:
    """Update an incident (optimistic locking via version field).

    The request must include the current version. If the incident was
    modified concurrently, returns 409 Conflict.
    """
    try:
        iid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid ID: {incident_id}")

    existing = await service.incident_repo.get_by_id(iid)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    # Merge update fields onto existing entity
    updated = existing.model_copy(
        update={
            k: v
            for k, v in {
                "title": request.title,
                "category": request.category,
                "severity": request.severity,
                "anti_pattern": request.anti_pattern,
                "remediation": request.remediation,
                "date": request.date,
                "organization": request.organization,
                "affected_languages": request.affected_languages,
                "code_example": request.code_example,
                "tags": request.tags,
                "static_rule_possible": request.static_rule_possible,
                "semgrep_rule_id": request.semgrep_rule_id,
            }.items()
            if v is not None
        }
    )

    try:
        saved = await service.update_incident(updated, expected_version=request.version)
    except OptimisticLockError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    return IncidentResponse.from_entity(saved)


@router.delete("/{incident_id}", status_code=204)
async def delete_incident(
    incident_id: str,
    service: IncidentSvc,
) -> None:
    """Soft-delete an incident (sets deleted_at).

    Returns 409 if the incident has an active Semgrep rule linked.
    Returns 204 No Content on success.
    """
    try:
        iid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid ID: {incident_id}")

    try:
        await service.soft_delete_incident(
            iid,
            tenant_id=SYSTEM_USER_ID,  # TODO: replace with auth tenant
        )
    except IncidentHasActiveRuleError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
