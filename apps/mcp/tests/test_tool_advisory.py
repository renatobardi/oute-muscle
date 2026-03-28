"""get_incident_advisory tool unit tests."""

import uuid

import pytest

from apps.mcp.src.metering import MeteringService, QuotaExceededError
from apps.mcp.src.tools.get_incident_advisory import get_incident_advisory


@pytest.mark.asyncio
async def test_advisory_returns_text():
    """mock RAG pipeline → returns advisory text."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "import re; re.compile('(.*)*')"

    result = await get_incident_advisory(
        code=code,
        context=None,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert "advisory_text" in result
    assert isinstance(result["advisory_text"], str)


@pytest.mark.asyncio
async def test_advisory_includes_confidence():
    """result has confidence field 0.0-1.0."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "x = 1"

    result = await get_incident_advisory(
        code=code,
        context=None,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_advisory_includes_incident_ids():
    """matched incidents returned in result."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "code with issues"

    result = await get_incident_advisory(
        code=code,
        context=None,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert "incident_ids" in result
    assert isinstance(result["incident_ids"], list)


@pytest.mark.asyncio
async def test_advisory_metering_tracked():
    """metering.increment() called."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    code = "x = 1"

    await get_incident_advisory(
        code=code,
        context=None,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    count = metering.get_count(user_id)
    assert count == 1


@pytest.mark.asyncio
async def test_advisory_blocked_at_quota():
    """quota exceeded → raises QuotaExceededError."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Fill quota
    for _ in range(50):
        metering.increment(user_id, "free")

    code = "x = 1"

    with pytest.raises(QuotaExceededError):
        await get_incident_advisory(
            code=code,
            context=None,
            tenant_id=tenant_id,
            user_id=user_id,
            tier="free",
            metering=metering,
        )
