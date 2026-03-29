"""Integration tests for Vertex AI Gemini Pro adapter.

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
async def test_pro_generate_returns_string() -> None:
    """Basic generation with Pro returns non-empty string."""
    from apps.api.src.adapters.vertex_llm import VertexGeminiPro

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    adapter = VertexGeminiPro(project_id=project_id)
    result = await adapter.generate("Say hello in one word.")

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_pro_model_name() -> None:
    """Pro adapter uses correct model identifier."""
    from apps.api.src.adapters.vertex_llm import VertexGeminiPro

    assert VertexGeminiPro.MODEL == "gemini-2.5-pro-preview-03-25"
