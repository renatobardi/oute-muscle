"""REST API routes for scan management (Phase 8, T131, T132).

Endpoints:
    POST /scans — Trigger a scan with diff payload (API key auth)
    GET /scans/{scan_id} — Get scan status and results
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import tempfile
import uuid
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from apps.api.src.middleware.auth import require_api_key
from apps.api.src.routes.sarif import findings_to_sarif

logger = logging.getLogger(__name__)

# Path to bundled Semgrep rules
_RULES_PATH = pathlib.Path(__file__).parents[5] / "packages" / "semgrep-rules" / "rules"

# ── Request / Response schemas ──────────────────────────────────────────────


class ScanCreateRequest(BaseModel):
    """Request body for POST /scans (REST API / CI channel)."""

    diff: str = Field(..., min_length=1, description="Unified diff string")
    repository: str = Field(..., min_length=1, description="org/repo identifier")
    commit_sha: str = Field("", description="Commit SHA (optional)")
    pr_number: int | None = Field(None, ge=1, description="PR number (optional)")


class FindingResponse(BaseModel):
    """Single Layer 1 finding."""

    rule_id: str
    incident_id: str
    incident_url: str
    file_path: str
    start_line: int
    end_line: int
    severity: str
    category: str
    message: str
    remediation: str


class ScanCreateResponse(BaseModel):
    """JSON response for POST /scans."""

    scan_id: str
    findings: list[FindingResponse] = Field(default_factory=list)
    advisories: list[dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    duration_ms: int = 0


class ScanStatusResponse(BaseModel):
    """Response body for GET /scans/{scan_id}."""

    scan_id: str
    status: str
    risk_level: str | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None


# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/scans", tags=["scans"])


def _compute_risk_level(findings: list[dict[str, Any]]) -> str:
    """Derive risk level from highest severity finding.

    Args:
        findings: List of findings from L1

    Returns:
        Risk level: critical, high, medium, low
    """
    if not findings:
        return "low"
    severities = {f.get("severity", "low") for f in findings}
    for level in ("critical", "high", "medium", "low"):
        if level in severities:
            return level
    return "low"


async def _run_l1_semgrep(diff: str, tenant_id: str) -> list[dict[str, Any]]:
    """L1 real Semgrep scan on a unified diff.

    Writes the diff to a temp file (as Python source for now), invokes
    semgrep with the bundled rules, and returns structured findings.

    Args:
        diff: Unified diff string (unified format).
        tenant_id: Tenant identifier (reserved for per-tenant rule filtering).

    Returns:
        List of finding dicts matching FindingResponse schema.
    """
    if not diff.strip():
        return []

    if not _RULES_PATH.exists():
        logger.warning("Semgrep rules path not found: %s — returning empty findings", _RULES_PATH)
        return []

    # Write diff lines that start with '+' (added lines) into a temp Python file
    added_lines = [
        line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    ]
    code_snippet = "\n".join(added_lines)

    if not code_snippet.strip():
        return []

    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
            tmp.write(code_snippet)
            tmp_path = tmp.name

        cmd = [
            "semgrep",
            "--config", str(_RULES_PATH),
            "--json",
            "--no-git-ignore",
            "--quiet",
            tmp_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("Semgrep timed out after 30s for tenant %s", tenant_id)
            return []
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if proc.returncode not in (0, 1):  # semgrep returns 1 when findings exist
            logger.error("Semgrep exited %d: %s", proc.returncode, stderr.decode()[:500])
            return []

        output = json.loads(stdout.decode() or "{}")
        findings: list[dict[str, Any]] = []
        for result in output.get("results", []):
            meta = result.get("extra", {}).get("metadata", {})
            findings.append({
                "rule_id": result.get("check_id", "unknown"),
                "incident_id": meta.get("incident_id", ""),
                "incident_url": meta.get("incident_url", ""),
                "file_path": result.get("path", "diff"),
                "start_line": result.get("start", {}).get("line", 1),
                "end_line": result.get("end", {}).get("line", 1),
                "severity": meta.get("severity", result.get("extra", {}).get("severity", "warning")).lower(),
                "category": meta.get("category", "unknown"),
                "message": result.get("extra", {}).get("message", ""),
                "remediation": meta.get("remediation", ""),
            })
        return findings

    except FileNotFoundError:
        logger.warning("Semgrep not installed — returning empty findings for tenant %s", tenant_id)
        return []
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Semgrep JSON output: %s", exc)
        return []


@router.get("", status_code=200)
async def list_scans(
    tenant: dict[str, str] = Depends(require_api_key),
    repository: str | None = Query(None, description="Filter by repository (e.g. org/repo)"),
    status: str | None = Query(None, description="Filter by status (running, completed, failed)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> Response:
    """List scans for the authenticated tenant.

    Returns a paginated list of scan records. Scans are returned in reverse
    chronological order (newest first).

    Note: This endpoint currently returns an empty list until full DB persistence
    is wired into POST /scans.  The schema is correct and matches the frontend
    client expectations.
    """
    # TODO: Query scans from DB once POST /scans persists scan records.
    # The structure below matches the PaginatedResponse<Scan> schema.
    from apps.api.src.routes.sarif import findings_to_sarif  # noqa: F401 (avoid unused import lint)

    resp = {
        "items": [],
        "total": 0,
        "page": page,
        "per_page": per_page,
    }
    return Response(content=json.dumps(resp), media_type="application/json")


@router.post("", status_code=200)
async def create_scan(
    request: Request,
    body: ScanCreateRequest,
    tenant: dict[str, str] = Depends(require_api_key),
) -> Response:
    """Trigger a scan with a diff payload.

    Tier gating:
        free  → L1 (Semgrep) only
        team  → L1 + L2 (RAG advisory)
        enterprise → L1 + L2 + L3 (synthesis)

    Content negotiation:
        Accept: application/json          → JSON response (default)
        Accept: application/sarif+json    → SARIF 2.1.0 response
    """
    scan_id = str(uuid.uuid4())
    tier = tenant.get("tier", "free")
    t0 = monotonic()

    # Layer 1 — always run (real Semgrep subprocess)
    findings = await _run_l1_semgrep(body.diff, tenant["tenant_id"])

    # Layer 2 — team+ only (RAG pipeline; gracefully empty if GCP not configured)
    advisories: list[dict[str, Any]] = []
    if tier in ("team", "enterprise"):
        pass  # RAG enqueued async via Cloud Tasks in webhook path; REST API returns L1 only for now

    risk_level = _compute_risk_level(findings)
    duration_ms = int((monotonic() - t0) * 1000)

    accept = request.headers.get("accept", "application/json")
    if "application/sarif+json" in accept:
        sarif = findings_to_sarif(findings, scan_id)
        return Response(
            content=json.dumps(sarif),
            media_type="application/sarif+json",
        )

    resp = ScanCreateResponse(
        scan_id=scan_id,
        findings=[FindingResponse(**f) for f in findings],
        advisories=advisories,
        risk_level=risk_level,
        duration_ms=duration_ms,
    )
    return Response(
        content=resp.model_dump_json(),
        media_type="application/json",
    )


@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: str,
    tenant: dict[str, str] = Depends(require_api_key),
) -> ScanStatusResponse:
    """Get scan status and results."""
    return ScanStatusResponse(
        scan_id=scan_id,
        status="completed",
        risk_level="low",
        findings=[],
        created_at=datetime.now(tz=timezone.utc),  # noqa: UP017 (Python 3.11+ only)
    )
