"""scan_code tool unit tests."""

import uuid
from unittest.mock import patch

import pytest

from apps.mcp.src.metering import MeteringService, QuotaExceededError
from apps.mcp.src.tools.scan_code import scan_code


@pytest.mark.asyncio
async def test_scan_code_returns_findings():
    """mock Semgrep runner → returns list of Finding dicts."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "print('hello')"

    with patch("apps.mcp.src.tools.scan_code.run_semgrep") as mock_semgrep:
        mock_semgrep.return_value = [
            {
                "rule_id": "unsafe-regex-001",
                "message": "Unsafe regex detected",
                "severity": "high",
                "line": 1,
                "incident_id": None,
            }
        ]

        result = await scan_code(
            code=code,
            language="python",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        assert "findings" in result
        assert isinstance(result["findings"], list)
        assert len(result["findings"]) > 0


@pytest.mark.asyncio
async def test_scan_code_no_findings_returns_empty():
    """clean code → empty list."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "x = 1"

    with patch("apps.mcp.src.tools.scan_code.run_semgrep") as mock_semgrep:
        mock_semgrep.return_value = []

        result = await scan_code(
            code=code,
            language="python",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        assert result["findings"] == []


@pytest.mark.asyncio
async def test_scan_code_includes_incident_refs():
    """finding matches rule with incident_id → incident_id in result."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    incident_id = str(uuid.uuid4())
    code = "import re; re.compile('(.*)*')"

    with patch("apps.mcp.src.tools.scan_code.run_semgrep") as mock_semgrep:
        mock_semgrep.return_value = [
            {
                "rule_id": "unsafe-regex-001",
                "message": "Unsafe regex",
                "severity": "critical",
                "line": 1,
                "incident_id": incident_id,
            }
        ]

        result = await scan_code(
            code=code,
            language="python",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        assert len(result["findings"]) > 0
        assert result["findings"][0]["incident_id"] == incident_id


@pytest.mark.asyncio
async def test_scan_code_respects_metering():
    """calls metering.increment() for each tool invocation."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "x = 1"

    with patch("apps.mcp.src.tools.scan_code.run_semgrep") as mock_semgrep:
        mock_semgrep.return_value = []

        await scan_code(
            code=code,
            language="python",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        count = metering.get_count(user_id)
        assert count == 1


@pytest.mark.asyncio
async def test_scan_code_blocked_at_quota():
    """quota exceeded → raises QuotaExceededError."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Fill quota for free tier (50)
    for _ in range(50):
        metering.increment(user_id, "free")

    code = "x = 1"

    with pytest.raises(QuotaExceededError):
        await scan_code(
            code=code,
            language="python",
            tenant_id=tenant_id,
            user_id=user_id,
            tier="free",
            metering=metering,
        )
