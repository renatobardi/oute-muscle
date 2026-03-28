"""
Waitlist endpoint for beta access requests.

POST /v1/waitlist  — register email for early access
GET  /v1/waitlist  — list entries (admin only, no auth enforced yet for beta)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    company: str | None = None
    source: str = "landing"

    @field_validator("name", "company", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class WaitlistResponse(BaseModel):
    id: str
    email: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Join the waitlist",
    response_model=WaitlistResponse,
)
async def join_waitlist(payload: WaitlistRequest, request: Request) -> JSONResponse:
    """Register an email address for early beta access."""
    session_factory = getattr(request.app.state, "session_factory", None)

    if session_factory is None:
        # No DB configured yet — store in memory log for early testing
        logger.info(
            "Waitlist signup (no-db mode)",
            extra={"email": payload.email, "company": payload.company},
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "id": "pending",
                "email": payload.email,
                "message": "You're on the list! We'll reach out soon.",
            },
        )

    try:
        import uuid

        from sqlalchemy import text

        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO waitlist (id, email, name, company, source)
                    VALUES (:id, :email, :name, :company, :source)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "email": str(payload.email),
                    "name": payload.name,
                    "company": payload.company,
                    "source": payload.source,
                },
            )
            row = result.fetchone()
            await session.commit()

        if row is None:
            # Email already registered — return 200 (don't leak existence via 409)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "id": "existing",
                    "email": str(payload.email),
                    "message": "You're already on the list!",
                },
            )

        logger.info("Waitlist signup", extra={"email": payload.email, "id": str(row[0])})
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "id": str(row[0]),
                "email": str(payload.email),
                "message": "You're on the list! We'll reach out soon.",
            },
        )

    except Exception as exc:
        logger.exception("Failed to insert waitlist entry", extra={"email": payload.email})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to register. Please try again."},
        )
