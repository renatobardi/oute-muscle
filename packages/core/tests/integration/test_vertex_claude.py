"""Integration tests for Vertex AI Claude Sonnet 4 adapter.

Constitution V: Skip if GOOGLE_CLOUD_PROJECT not set.
Tests real Vertex AI API calls, not mocks.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_CLOUD_PROJECT"),
    reason="requires GOOGLE_CLOUD_PROJECT env var",
)


@pytest.mark.asyncio
async def test_claude_generate_returns_string() -> None:
    """Basic generation with Claude returns non-empty string."""
    from src.adapters.vertex_claude import VertexClaudeSonnet4

    adapter = VertexClaudeSonnet4()
    result = await adapter.generate("Say hello in one word.")

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_claude_model_name() -> None:
    """Claude adapter uses correct model identifier."""
    from src.adapters.vertex_claude import VertexClaudeSonnet4

    assert VertexClaudeSonnet4.MODEL == "claude-sonnet-4@20251101"
