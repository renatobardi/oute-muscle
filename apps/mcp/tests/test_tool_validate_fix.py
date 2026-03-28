"""validate_fix tool unit tests."""

import uuid
from unittest.mock import patch

import pytest

from apps.mcp.src.metering import MeteringService, QuotaExceededError
from apps.mcp.src.tools.validate_fix import validate_fix


@pytest.mark.asyncio
async def test_validate_fix_returns_pass_when_clean():
    """re-scan finds no findings → {"status": "pass"}."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    original_code = "import re; re.compile('(.*)*')"
    fixed_code = "import re; re.compile('a+')"

    with patch("apps.mcp.src.tools.validate_fix.scan_code") as mock_scan:
        mock_scan.return_value = {"findings": [], "scan_id": str(uuid.uuid4())}

        result = await validate_fix(
            original_code=original_code,
            fixed_code=fixed_code,
            rule_id="unsafe-regex-001",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        assert result["status"] == "pass"


@pytest.mark.asyncio
async def test_validate_fix_returns_fail_when_still_flagged():
    """re-scan still finds issue → {"status": "fail", "remaining_findings": [...]}."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    original_code = "import re; re.compile('(.*)*')"
    fixed_code = "import re; re.compile('(.*)*')"  # Same issue

    with patch("apps.mcp.src.tools.validate_fix.scan_code") as mock_scan:
        mock_scan.return_value = {
            "findings": [
                {
                    "rule_id": "unsafe-regex-001",
                    "message": "Unsafe regex",
                    "severity": "critical",
                    "line": 1,
                }
            ],
            "scan_id": str(uuid.uuid4()),
        }

        result = await validate_fix(
            original_code=original_code,
            fixed_code=fixed_code,
            rule_id="unsafe-regex-001",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        assert result["status"] == "fail"
        assert "remaining_findings" in result
        assert len(result["remaining_findings"]) > 0


@pytest.mark.asyncio
async def test_validate_fix_metering_tracked():
    """metering.increment() called."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    with patch("apps.mcp.src.tools.validate_fix.scan_code") as mock_scan:
        mock_scan.return_value = {"findings": [], "scan_id": str(uuid.uuid4())}

        await validate_fix(
            original_code="x = 1",
            fixed_code="y = 2",
            rule_id="test-rule",
            tenant_id=tenant_id,
            user_id=user_id,
            metering=metering,
        )

        count = metering.get_count(user_id)
        assert count == 1


@pytest.mark.asyncio
async def test_validate_fix_blocked_at_quota():
    """quota exceeded → raises QuotaExceededError."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Fill quota
    for _ in range(50):
        metering.increment(user_id, "free")

    with pytest.raises(QuotaExceededError):
        await validate_fix(
            original_code="x = 1",
            fixed_code="y = 2",
            rule_id="test-rule",
            tenant_id=tenant_id,
            user_id=user_id,
            tier="free",
            metering=metering,
        )
