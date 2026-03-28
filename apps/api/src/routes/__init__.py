"""API routes for Oute Muscle."""

from __future__ import annotations

from .incidents import router as incidents_router

__all__ = ["incidents_router"]
