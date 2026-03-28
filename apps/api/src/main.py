"""FastAPI application entry point — DI container, middleware stack, route registration.

Constitution VI: Hexagonal boundaries with ports/adapters.
No external dependencies or secrets in this layer.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DIContainer:
    """Dependency injection container for FastAPI.

    Populated with concrete implementations of all ports.
    """

    def __init__(self) -> None:
        """Initialize empty container. Populated at app startup."""
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager — startup and shutdown."""
    # Startup
    logger.info("Starting Oute Muscle API")
    # TODO: Initialize DI container with adapters
    # TODO: Connect to PostgreSQL
    # TODO: Verify Vertex AI credentials

    yield

    # Shutdown
    logger.info("Shutting down Oute Muscle API")
    # TODO: Close database connections
    # TODO: Clean up resources


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Oute Muscle API",
        description="Incident-based code guardrails platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure from environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):  # type: ignore[no-untyped-def]
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_SERVER_ERROR",
            },
        )

    # Health check
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Register routes — Phase 4: incidents CRUD
    from apps.api.src.routes.incidents import router as incidents_router

    app.include_router(incidents_router, prefix="/v1")

    # Phase 5: scans and advisory routes
    from apps.api.src.routes.scans import router as scans_router

    app.include_router(scans_router, prefix="/v1")

    # Phase 6: GitHub webhook routes
    from apps.api.src.routes.webhooks import router as webhooks_router

    app.include_router(webhooks_router, prefix="/v1")

    # Phase 5+: rules, advisory routes added as phases complete

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
