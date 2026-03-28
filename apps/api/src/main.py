"""FastAPI application entry point — DI container, middleware stack, route registration.

Constitution VI: Hexagonal boundaries with ports/adapters.
The DI container wires real adapters to domain services at startup.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.src.config import configure_logging, settings

logger = logging.getLogger(__name__)


class DIContainer:
    """Dependency injection container — holds app-level singletons.

    Per-request resources (DB sessions, scoped services) are created via
    FastAPI Depends() in apps/api/src/dependencies.py.
    """

    def __init__(self) -> None:
        from apps.api.src.adapters.vertex_embedding import make_embedding_adapter
        from packages.db.src.session import SessionFactory

        # Database — single session factory for the whole app
        self.session_factory = SessionFactory(
            database_url=settings.database_url,
            echo=(settings.log_level == "DEBUG"),
        )

        # Vertex AI embedding adapter (null if GCP not configured)
        gcp_project = settings.gcp_project_id or None
        self.embedding_adapter = make_embedding_adapter(
            project_id=gcp_project,
            location=settings.vertex_location,
        )

        # LLM adapters — lazy-init inside VertexGemini*/VertexClaude classes
        if gcp_project:
            from apps.api.src.adapters.vertex_llm import (
                VertexClaudeSonnet,
                VertexGeminiFlash,
                VertexGeminiPro,
            )

            self.llm_flash = VertexGeminiFlash(
                project_id=gcp_project, location=settings.vertex_location
            )
            self.llm_pro = VertexGeminiPro(
                project_id=gcp_project, location=settings.vertex_location
            )
            self.llm_claude = VertexClaudeSonnet(
                project_id=gcp_project, location="us-east5"
            )
        else:
            from apps.api.src.adapters.vertex_llm import NullLLMAdapter

            self.llm_flash = NullLLMAdapter()  # type: ignore[assignment]
            self.llm_pro = NullLLMAdapter()  # type: ignore[assignment]
            self.llm_claude = NullLLMAdapter()  # type: ignore[assignment]

        logger.info(
            "di_container_initialized",
            gcp_configured=bool(gcp_project),
            database_url=settings.database_url[:30] + "...",
        )

    async def close(self) -> None:
        """Gracefully close all connections."""
        await self.session_factory.close()
        logger.info("di_container_closed")


# App-level singleton — set during lifespan startup
_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Return the app-level DI container. Must be called after startup."""
    if _container is None:
        raise RuntimeError("DIContainer not initialized — app not started yet")
    return _container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize and teardown all resources."""
    global _container

    configure_logging()
    logger.info("starting_oute_muscle_api", version="0.1.0")

    _container = DIContainer()
    logger.info("startup_complete")

    yield

    logger.info("shutting_down_oute_muscle_api")
    if _container:
        await _container.close()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Oute Muscle API",
        description="Incident-based code guardrails platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict via env var in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware stack — add_middleware in reverse execution order
    # (last added = outermost = first to process the request)
    from apps.api.src.middleware.rate_limit import RateLimitMiddleware
    from apps.api.src.middleware.correlation import CorrelationMiddleware

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CorrelationMiddleware)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):  # type: ignore[no-untyped-def]
        logger.exception("unhandled_exception", path=str(request.url.path))
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "code": "INTERNAL_SERVER_ERROR"},
        )

    # Health check (public, no auth)
    from apps.api.src.routes.health import router as health_router

    app.include_router(health_router)

    # Waitlist (public, no auth — landing page)
    from apps.api.src.routes.waitlist import router as waitlist_router

    app.include_router(waitlist_router, prefix="/v1")

    # Incidents CRUD (Phase 4)
    from apps.api.src.routes.incidents import router as incidents_router

    app.include_router(incidents_router, prefix="/v1")

    # Scans + Advisory (Phase 5)
    from apps.api.src.routes.scans import router as scans_router

    app.include_router(scans_router, prefix="/v1")

    # GitHub webhooks (Phase 6)
    from apps.api.src.routes.webhooks import router as webhooks_router

    app.include_router(webhooks_router, prefix="/v1")

    # Tenant management (Phase 10)
    from apps.api.src.routes.tenants import router as tenants_router

    app.include_router(tenants_router, prefix="/v1")

    # Audit log (Phase 10, Enterprise)
    from apps.api.src.routes.audit import router as audit_router

    app.include_router(audit_router, prefix="/v1")

    # Findings (Phase 12)
    from apps.api.src.routes.findings import router as findings_router

    app.include_router(findings_router, prefix="/v1")

    # Synthesis candidates (Phase 11)
    from apps.api.src.routes.synthesis import router as synthesis_router

    app.include_router(synthesis_router, prefix="/v1")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
