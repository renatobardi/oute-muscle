"""
T161: Correlation ID middleware for request tracing.

Reads X-Correlation-ID from the incoming request (or generates a new UUID v4
if absent), attaches it to request.state.correlation_id, and echoes it back
in the response X-Correlation-ID header.

All structured log entries in the same request automatically pick up the
correlation ID from contextvars (bound by structlog's AsyncBoundLogger).
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# Module-level ContextVar so any code in the same async task can read it
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

HEADER_NAME = "X-Correlation-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    - Reads X-Correlation-ID from request headers (forwarded from caller).
    - Falls back to a freshly generated UUID v4.
    - Stores it in:
        request.state.correlation_id
        correlation_id_ctx  (ContextVar, accessible anywhere in the call chain)
    - Echoes it back in the response header.
    """

    def __init__(self, app: ASGIApp, header_name: str = HEADER_NAME) -> None:
        super().__init__(app)
        self._header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cid = request.headers.get(self._header_name) or str(uuid.uuid4())

        # Store in request state (accessible in route handlers via request.state)
        request.state.correlation_id = cid

        # Store in ContextVar (accessible in any coroutine without passing request around)
        token = correlation_id_ctx.set(cid)

        try:
            response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)

        response.headers[self._header_name] = cid
        return response
