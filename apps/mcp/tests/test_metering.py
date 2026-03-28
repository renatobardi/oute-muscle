"""Metering unit tests."""

import uuid

from apps.mcp.src.metering import MeteringService


def test_new_user_has_zero_calls():
    """user with no history → 0 calls this month."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    count = metering.get_count(user_id)
    assert count == 0


def test_increment_tracks_calls():
    """after 3 calls → count is 3."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    metering.increment(user_id, "free")
    metering.increment(user_id, "free")
    metering.increment(user_id, "free")

    count = metering.get_count(user_id)
    assert count == 3


def test_quota_not_exceeded_below_50():
    """49 calls → quota_ok() returns True."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    for _ in range(49):
        metering.increment(user_id, "free")

    assert metering.quota_ok(user_id, "free") is True


def test_quota_exceeded_at_50():
    """50 calls → quota_ok() returns False."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    for _ in range(50):
        metering.increment(user_id, "free")

    assert metering.quota_ok(user_id, "free") is False


def test_quota_exceeded_above_50():
    """51 calls → quota_ok() returns False."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    for _ in range(51):
        metering.increment(user_id, "free")

    assert metering.quota_ok(user_id, "free") is False


def test_quota_resets_next_month():
    """calls from last month don't count this month."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    # Add calls in "last month"
    metering._increment_internal(user_id, "free", months_offset=-1)

    # Current month should be 0
    current_count = metering.get_count(user_id)
    assert current_count == 0


def test_enterprise_user_has_unlimited_quota():
    """tier=enterprise → always quota_ok()."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    # Even with 1000 calls
    for _ in range(1000):
        metering.increment(user_id, "enterprise")

    assert metering.quota_ok(user_id, "enterprise") is True


def test_free_tier_limit_is_50():
    """tier=free → limit is 50."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    # Add exactly 50
    for _ in range(50):
        metering.increment(user_id, "free")

    # Should be at limit
    assert metering.quota_ok(user_id, "free") is False


def test_team_tier_limit_is_500():
    """tier=team → limit is 500."""
    metering = MeteringService()
    user_id = str(uuid.uuid4())

    # Add 499 - should be ok
    for _ in range(499):
        metering.increment(user_id, "team")

    assert metering.quota_ok(user_id, "team") is True

    # Add one more
    metering.increment(user_id, "team")
    # Now at 500 - should fail
    assert metering.quota_ok(user_id, "team") is False
