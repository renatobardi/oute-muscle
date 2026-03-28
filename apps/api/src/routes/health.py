"""
T175: Health and readiness probe endpoints.

GET /health/live    — liveness probe (always 200 if process is running)
GET /health/ready   — readiness probe (200 only when DB + LLM deps are reachable)
GET /health/startup — startup probe (200 after initial migrations/boot complete)

Cloud Run configuration:
  livenessProbe:  GET /health/live   (failure → restart container)
  readinessProbe: GET /health/ready  (failure → remove from load balancer)
  startupProbe:   GET /health/startup (failure → restart before liveness kicks in)
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])

_START_TIME = time.monotonic()


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class CheckResult(BaseModel):
    name: str
    status: str  # "ok" | "degraded" | "error"
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded" | "error"
    version: str
    uptime_seconds: float
    checks: list[CheckResult] = []


# ---------------------------------------------------------------------------
# Dependency check helpers
# ---------------------------------------------------------------------------


async def _check_database(request: Request) -> CheckResult:
    """Ping the database by executing SELECT 1."""
    t0 = time.monotonic()
    try:
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is None:
            return CheckResult(
                name="database", status="error", detail="session_factory not configured"
            )

        async with session_factory() as session:
            await session.execute("SELECT 1")

        return CheckResult(
            name="database",
            status="ok",
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )
    except Exception as exc:
        return CheckResult(
            name="database",
            status="error",
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            detail=str(exc),
        )


async def _check_llm_router(request: Request) -> CheckResult:
    """
    Light check: verify the LLM router is configured.
    We do NOT make an actual LLM call to avoid cost/latency on every probe.
    """
    t0 = time.monotonic()
    try:
        llm_router = getattr(request.app.state, "llm_router", None)
        if llm_router is None:
            return CheckResult(
                name="llm_router", status="error", detail="llm_router not configured"
            )
        # A real implementation might ping Vertex AI metadata endpoint
        return CheckResult(
            name="llm_router",
            status="ok",
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )
    except Exception as exc:
        return CheckResult(
            name="llm_router",
            status="error",
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            detail=str(exc),
        )


def _app_version(request: Request) -> str:
    return getattr(request.app.state, "version", "unknown")


def _is_ready(request: Request) -> bool:
    """True once the app has completed its startup sequence."""
    return getattr(request.app.state, "ready", False)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/live",
    summary="Liveness probe",
    response_model=HealthResponse,
)
async def liveness(request: Request) -> JSONResponse:
    """
    Always returns 200 as long as the process is running.
    Cloud Run uses this to decide whether to restart the container.
    """
    body = HealthResponse(
        status="ok",
        version=_app_version(request),
        uptime_seconds=round(time.monotonic() - _START_TIME, 2),
    )
    return JSONResponse(content=body.model_dump(), status_code=status.HTTP_200_OK)


@router.get(
    "/ready",
    summary="Readiness probe",
    response_model=HealthResponse,
)
async def readiness(request: Request) -> JSONResponse:
    """
    Returns 200 only when critical dependencies are healthy.
    Cloud Run removes the instance from the load balancer on failure.
    """
    db_check = await _check_database(request)
    llm_check = await _check_llm_router(request)
    checks = [db_check, llm_check]

    any_error = any(c.status == "error" for c in checks)
    overall = "error" if any_error else "ok"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE if any_error else status.HTTP_200_OK

    body = HealthResponse(
        status=overall,
        version=_app_version(request),
        uptime_seconds=round(time.monotonic() - _START_TIME, 2),
        checks=checks,
    )
    return JSONResponse(content=body.model_dump(), status_code=http_status)


@router.get(
    "/startup",
    summary="Startup probe",
    response_model=HealthResponse,
)
async def startup(request: Request) -> JSONResponse:
    """
    Returns 200 only after the application has finished its startup sequence
    (migrations applied, caches warmed, etc.).
    Cloud Run uses this before switching to liveness/readiness probes.
    """
    ready = _is_ready(request)
    http_status = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE

    body = HealthResponse(
        status="ok" if ready else "starting",
        version=_app_version(request),
        uptime_seconds=round(time.monotonic() - _START_TIME, 2),
    )
    return JSONResponse(content=body.model_dump(), status_code=http_status)
