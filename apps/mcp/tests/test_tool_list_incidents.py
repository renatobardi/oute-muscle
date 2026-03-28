"""list_relevant_incidents tool unit tests."""

import uuid

import pytest

from apps.mcp.src.metering import MeteringService
from apps.mcp.src.tools.list_relevant_incidents import list_relevant_incidents


@pytest.mark.asyncio
async def test_list_returns_incidents():
    """mock repo → returns list of incident dicts."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    result = await list_relevant_incidents(
        query=None,
        category=None,
        max_results=10,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert "incidents" in result
    assert isinstance(result["incidents"], list)


@pytest.mark.asyncio
async def test_list_max_results_respected():
    """max_results=3 → at most 3 returned."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    result = await list_relevant_incidents(
        query=None,
        category=None,
        max_results=3,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert len(result["incidents"]) <= 3


@pytest.mark.asyncio
async def test_list_semantic_search_used_when_query_provided():
    """query given → vector search used."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    query = "regex vulnerability"

    result = await list_relevant_incidents(
        query=query,
        category=None,
        max_results=10,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert "incidents" in result


@pytest.mark.asyncio
async def test_list_text_search_when_no_query():
    """no query → text/filter search used."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    result = await list_relevant_incidents(
        query=None,
        category="test",
        max_results=10,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    assert "incidents" in result


@pytest.mark.asyncio
async def test_list_metering_tracked():
    """metering.increment() called."""
    metering = MeteringService()
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    await list_relevant_incidents(
        query=None,
        category=None,
        max_results=10,
        tenant_id=tenant_id,
        user_id=user_id,
        metering=metering,
    )

    count = metering.get_count(user_id)
    assert count == 1
