"""T030: Unit tests for admin route auth guard."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apps.api.src.middleware.auth import require_admin


class TestRequireAdmin:
    """Test require_admin dependency."""

    @pytest.mark.asyncio
    async def test_admin_passes(self) -> None:
        request = MagicMock()
        request.state.role = "admin"
        await require_admin(request)  # Should not raise

    @pytest.mark.asyncio
    async def test_editor_blocked(self) -> None:
        request = MagicMock()
        request.state.role = "editor"
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_blocked(self) -> None:
        request = MagicMock()
        request.state.role = "viewer"
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_role_blocked(self) -> None:
        request = MagicMock()
        request.state.role = None
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(request)
        assert exc_info.value.status_code == 403
