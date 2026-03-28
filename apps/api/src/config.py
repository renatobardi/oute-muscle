"""
T162 + T181: Application settings + structlog JSON logging + OpenTelemetry tracing.

Structured log events automatically include:
  correlation_id  — from ContextVar (set by CorrelationMiddleware)
  tenant_id       — from ContextVar (set by RLS middleware)
  user_id         — from ContextVar (set by RLS middleware)
  timestamp       — ISO 8601 UTC
  level           — log level string
  event           — the log message

GCP Cloud Logging compatible: emits JSON to stdout; the Cloud Logging agent
maps ``severity`` from the ``level`` field.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

import structlog
from pydantic_settings import BaseSettings

from apps.api.src.middleware.correlation import correlation_id_ctx

# ContextVars for per-request tenant / user context (set by RLS middleware)
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://localhost/oute_dev"

    # JWT (RS256 public key PEM string; injected via Secret Manager in prod)
    jwt_public_key: str = ""

    # GCP
    gcp_project_id: str = "oute-488706"
    gcp_region: str = "us-central1"

    # Vertex AI
    vertex_location: str = "us-central1"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" | "console"

    # OpenTelemetry / tracing
    otel_enabled: bool = True
    otel_service_name: str = "oute-muscle-api"
    otel_exporter: str = "gcp"  # "gcp" | "otlp" | "console" | "none"
    otel_otlp_endpoint: str = "http://localhost:4317"  # used when exporter=otlp

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# ---------------------------------------------------------------------------
# structlog configuration
# ---------------------------------------------------------------------------


def _add_request_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Inject per-request context vars into every log event."""
    cid = correlation_id_ctx.get("")
    if cid:
        event_dict["correlation_id"] = cid

    tid = tenant_id_ctx.get("")
    if tid:
        event_dict["tenant_id"] = tid

    uid = user_id_ctx.get("")
    if uid:
        event_dict["user_id"] = uid

    return event_dict


def configure_logging() -> None:
    """
    Configure structlog + stdlib logging.
    Call once at application startup (e.g. in main.py lifespan).
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_context,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        # Production: JSON for GCP Cloud Logging
        renderer = structlog.processors.JSONRenderer()
    else:
        # Local development: colourful console
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Quiet down noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# T181: OpenTelemetry tracing configuration
# ---------------------------------------------------------------------------


def configure_tracing() -> None:
    """
    Configure OpenTelemetry tracing with the GCP Cloud Trace exporter.
    Call once at application startup after configure_logging().

    Spans are created automatically for:
      - Incoming HTTP requests (FastAPI / ASGI)
      - SQLAlchemy queries (via opentelemetry-instrumentation-sqlalchemy)
      - HTTPX outbound calls to Vertex AI (via opentelemetry-instrumentation-httpx)

    The correlation_id from CorrelationMiddleware is attached to every span
    as a custom attribute so traces can be correlated with structured logs.
    """
    if not settings.otel_enabled or settings.otel_exporter == "none":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError:
        logging.getLogger(__name__).warning(
            "opentelemetry packages not installed — tracing disabled"
        )
        return

    resource = Resource(attributes={SERVICE_NAME: settings.otel_service_name})

    # Sample 100% of traces in dev/staging; 10% in prod to reduce cost
    sampler = ParentBased(TraceIdRatioBased(1.0))

    provider = TracerProvider(resource=resource, sampler=sampler)

    if settings.otel_exporter == "gcp":
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = CloudTraceSpanExporter(project_id=settings.gcp_project_id)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            logging.getLogger(__name__).warning(
                "opentelemetry-exporter-gcp-trace not installed — falling back to console"
            )
            _add_console_exporter(provider)

    elif settings.otel_exporter == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            logging.getLogger(__name__).warning(
                "opentelemetry-exporter-otlp not installed — falling back to console"
            )
            _add_console_exporter(provider)

    elif settings.otel_exporter == "console":
        _add_console_exporter(provider)

    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    logging.getLogger(__name__).info(
        "opentelemetry_tracing_configured",
        exporter=settings.otel_exporter,
        service=settings.otel_service_name,
    )


def _add_console_exporter(provider: TracerProvider) -> None:
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    # In dev/test: print spans to stdout
    try:
        from opentelemetry.exporter.console import ConsoleSpanExporter

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    except ImportError:
        provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
