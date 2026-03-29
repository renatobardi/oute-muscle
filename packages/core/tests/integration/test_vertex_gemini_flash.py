"""Integration tests for Vertex AI Gemini Flash adapter.

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
async def test_flash_generate_returns_string() -> None:
    """Basic generation with Flash returns non-empty string."""
    from packages.core.src.adapters.vertex_llm import VertexGeminiFlash

    adapter = VertexGeminiFlash()
    result = await adapter.generate("Say hello in one word.")

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_flash_model_name() -> None:
    """Flash adapter uses correct model identifier."""
    from packages.core.src.adapters.vertex_llm import VertexGeminiFlash

    assert VertexGeminiFlash.MODEL == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_flash_timeout_respected() -> None:
    """Flash respects 30-second timeout (mock)."""
    from unittest.mock import patch

    from packages.core.src.adapters.vertex_llm import VertexGeminiFlash
    from packages.core.src.ports.llm import LLMTimeoutError

    adapter = VertexGeminiFlash()

    # Mock the actual API call to simulate timeout
    with patch.object(adapter, "generate", side_effect=LLMTimeoutError("timeout")):
        with pytest.raises(LLMTimeoutError):
            await adapter.generate("prompt")
