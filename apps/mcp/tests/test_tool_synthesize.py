"""synthesize_rules tool unit tests (Enterprise guard)."""

import uuid

import pytest

from apps.mcp.src.metering import MeteringService
from apps.mcp.src.tools.synthesize_rules import (
    EnterpriseTierRequiredError,
    synthesize_rules,
)


@pytest.mark.asyncio
async def test_synthesize_blocked_for_free_tier():
    """tier=free → raises EnterpriseTierRequired."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    with pytest.raises(EnterpriseTierRequiredError):
        await synthesize_rules(
            incident_ids=[str(uuid.uuid4())],
            tenant_id=tenant_id,
            user_id=user_id,
            tier="free",
            metering=metering,
        )


@pytest.mark.asyncio
async def test_synthesize_blocked_for_team_tier():
    """tier=team → raises EnterpriseTierRequired."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    with pytest.raises(EnterpriseTierRequiredError):
        await synthesize_rules(
            incident_ids=[str(uuid.uuid4())],
            tenant_id=tenant_id,
            user_id=user_id,
            tier="team",
            metering=metering,
        )


@pytest.mark.asyncio
async def test_synthesize_allowed_for_enterprise():
    """tier=enterprise → proceeds."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    incident_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    result = await synthesize_rules(
        incident_ids=incident_ids,
        tenant_id=tenant_id,
        user_id=user_id,
        tier="enterprise",
        metering=metering,
    )

    assert "candidate_id" in result
    assert result["status"] == "queued"


@pytest.mark.asyncio
async def test_synthesize_creates_candidate():
    """enterprise tier → creates SynthesisCandidate record."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    incident_ids = [str(uuid.uuid4())]

    result = await synthesize_rules(
        incident_ids=incident_ids,
        tenant_id=tenant_id,
        user_id=user_id,
        tier="enterprise",
        metering=metering,
    )

    assert "candidate_id" in result
    assert result["status"] == "queued"


@pytest.mark.asyncio
async def test_synthesize_metering_tracked():
    """called only if enterprise."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    await synthesize_rules(
        incident_ids=[str(uuid.uuid4())],
        tenant_id=tenant_id,
        user_id=user_id,
        tier="enterprise",
        metering=metering,
    )

    count = metering.get_count(user_id)
    assert count == 1
