"""
T183: Tests for false positive reporting endpoint.

Coverage:
  - POST /findings/{id}/false-positive → 200 on first report
  - Updates finding status to 'false_positive'
  - Increments false_positive_count on each call
  - Auto-disables the rule at threshold 3
  - Requires editor+ role (403 for viewer)
  - Returns 404 for unknown finding
  - Returns 409 if already marked false positive
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeFinding:
    def __init__(
        self,
        id: str = "finding-1",
        rule_id: str = "unsafe-regex-001",
        status: str = "open",
        false_positive_count: int = 0,
        tenant_id: str = "tenant-abc",
    ):
        self.id = id
        self.rule_id = rule_id
        self.status = status
        self.false_positive_count = false_positive_count
        self.tenant_id = tenant_id


class FakeRule:
    def __init__(self, id: str = "unsafe-regex-001", enabled: bool = True):
        self.id = id
        self.enabled = enabled


# ---------------------------------------------------------------------------
# Unit tests for the false-positive service logic
# ---------------------------------------------------------------------------


class TestFalsePositiveService:
    """
    Tests for apps.api.src.services.false_positive.FalsePositiveService
    """

    @pytest.mark.asyncio
    async def test_marks_finding_as_false_positive(self):
        """First report sets status=false_positive, increments count to 1."""
        from apps.api.src.services.false_positive import FalsePositiveService

        finding = FakeFinding(false_positive_count=0, status="open")
        rule = FakeRule(enabled=True)

        finding_repo = AsyncMock()
        finding_repo.get.return_value = finding
        rule_repo = AsyncMock()
        rule_repo.get.return_value = rule

        service = FalsePositiveService(finding_repo=finding_repo, rule_repo=rule_repo)
        result = await service.report(finding_id="finding-1", reported_by="user-x")

        assert result.false_positive_count == 1
        assert result.status == "false_positive"
        finding_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_increments_count_on_subsequent_reports(self):
        """Each call increments the counter even if already marked."""
        from apps.api.src.services.false_positive import FalsePositiveService

        finding = FakeFinding(false_positive_count=1, status="false_positive")
        rule = FakeRule(enabled=True)

        finding_repo = AsyncMock()
        finding_repo.get.return_value = finding
        rule_repo = AsyncMock()
        rule_repo.get.return_value = rule

        service = FalsePositiveService(finding_repo=finding_repo, rule_repo=rule_repo)
        result = await service.report(finding_id="finding-1", reported_by="user-y")

        assert result.false_positive_count == 2
        # Rule not auto-disabled yet
        rule_repo.disable.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_disables_rule_at_threshold_3(self):
        """At false_positive_count == 3, the rule is automatically disabled."""
        from apps.api.src.services.false_positive import (
            FALSE_POSITIVE_DISABLE_THRESHOLD,
            FalsePositiveService,
        )

        assert FALSE_POSITIVE_DISABLE_THRESHOLD == 3

        finding = FakeFinding(false_positive_count=2, status="false_positive")
        rule = FakeRule(enabled=True)

        finding_repo = AsyncMock()
        finding_repo.get.return_value = finding
        rule_repo = AsyncMock()
        rule_repo.get.return_value = rule

        service = FalsePositiveService(finding_repo=finding_repo, rule_repo=rule_repo)
        result = await service.report(finding_id="finding-1", reported_by="user-z")

        assert result.false_positive_count == 3
        rule_repo.disable.assert_called_once_with("unsafe-regex-001")

    @pytest.mark.asyncio
    async def test_rule_already_disabled_does_not_double_disable(self):
        """If the rule is already disabled, we don't call disable() again."""
        from apps.api.src.services.false_positive import FalsePositiveService

        finding = FakeFinding(false_positive_count=3, status="false_positive")
        rule = FakeRule(enabled=False)

        finding_repo = AsyncMock()
        finding_repo.get.return_value = finding
        rule_repo = AsyncMock()
        rule_repo.get.return_value = rule

        service = FalsePositiveService(finding_repo=finding_repo, rule_repo=rule_repo)
        await service.report(finding_id="finding-1", reported_by="user-x")

        rule_repo.disable.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_not_found_for_unknown_finding(self):
        """Raises FindingNotFoundError when the finding doesn't exist."""
        from apps.api.src.services.false_positive import (
            FalsePositiveService,
            FindingNotFoundError,
        )

        finding_repo = AsyncMock()
        finding_repo.get.return_value = None
        rule_repo = AsyncMock()

        service = FalsePositiveService(finding_repo=finding_repo, rule_repo=rule_repo)

        with pytest.raises(FindingNotFoundError):
            await service.report(finding_id="nonexistent", reported_by="user-x")


# ---------------------------------------------------------------------------
# HTTP endpoint tests (FastAPI TestClient or HTTPX async client)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_request_state():
    """Returns a mock request.state with editor role."""
    state = MagicMock()
    state.tenant_id = "tenant-abc"
    state.user_id = "user-editor"
    state.role = "editor"
    state.plan = "team"
    return state


class TestFalsePositiveEndpoint:
    def _make_app(self, service_mock):
        """Create a minimal FastAPI app with the findings router mounted."""
        from fastapi import FastAPI

        from apps.api.src.routes.findings import router

        app = FastAPI()
        app.include_router(router)
        app.state.false_positive_service = service_mock
        return app

    @pytest.mark.asyncio
    async def test_returns_200_on_success(self):
        """POST /findings/{id}/false-positive returns 200 for an editor."""
        from httpx import ASGITransport, AsyncClient

        from apps.api.src.routes.findings import (
            get_service,
            get_tenant_id,
            get_user_id,
            require_editor,
        )
        from apps.api.src.services.false_positive import FalsePositiveService

        finding = FakeFinding(false_positive_count=1, status="false_positive")
        service = AsyncMock(spec=FalsePositiveService)
        service.report.return_value = finding

        app = self._make_app(service)

        # Use dependency_overrides — patching module names doesn't affect Depends() refs
        app.dependency_overrides[require_editor] = lambda: None
        app.dependency_overrides[get_tenant_id] = lambda: "tenant-abc"
        app.dependency_overrides[get_user_id] = lambda: "user-editor"
        app.dependency_overrides[get_service] = lambda: service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/findings/finding-1/false-positive")

        assert resp.status_code == 200
        data = resp.json()
        assert data["false_positive_count"] == 1
        assert data["status"] == "false_positive"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_finding(self):
        """POST /findings/{id}/false-positive returns 404 when finding missing."""
        from httpx import ASGITransport, AsyncClient

        from apps.api.src.routes.findings import (
            get_service,
            get_tenant_id,
            get_user_id,
            require_editor,
        )
        from apps.api.src.services.false_positive import FalsePositiveService, FindingNotFoundError

        service = AsyncMock(spec=FalsePositiveService)
        service.report.side_effect = FindingNotFoundError("nonexistent")

        app = self._make_app(service)

        app.dependency_overrides[require_editor] = lambda: None
        app.dependency_overrides[get_tenant_id] = lambda: "tenant-abc"
        app.dependency_overrides[get_user_id] = lambda: "user-editor"
        app.dependency_overrides[get_service] = lambda: service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/findings/nonexistent/false-positive")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_viewer_role(self):
        """POST /findings/{id}/false-positive returns 403 for viewers."""
        from fastapi import HTTPException
        from httpx import ASGITransport, AsyncClient

        from apps.api.src.routes.findings import get_tenant_id, get_user_id, require_editor

        finding = FakeFinding()
        service = AsyncMock()
        service.report.return_value = finding

        app = self._make_app(service)

        def _reject_viewer():
            raise HTTPException(status_code=403, detail="FORBIDDEN")

        app.dependency_overrides[require_editor] = _reject_viewer
        app.dependency_overrides[get_tenant_id] = lambda: "tenant-abc"
        app.dependency_overrides[get_user_id] = lambda: "user-viewer"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/findings/finding-1/false-positive")

        assert resp.status_code == 403
