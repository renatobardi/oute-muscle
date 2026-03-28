"""Vertex AI LLM adapters — Gemini Flash and Pro (LLMPort implementations).

Constitution V: All LLM access via Vertex AI. Models:
  - Gemini 2.5 Flash (fast triage)
  - Gemini 2.5 Pro (medium complexity)

30-second timeout per Constitution V → asyncio.wait_for(coro, timeout=30.0)
Gracefully skip if GOOGLE_CLOUD_PROJECT not set.
"""

from __future__ import annotations

import os
from typing import Any

from ..ports.llm import LLMError, LLMPort, LLMTimeoutError


class VertexGeminiFlash(LLMPort):
    """Vertex AI Gemini 2.5 Flash adapter (LLMPort implementation)."""

    MODEL: str = "gemini-2.5-flash"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Generate text using Gemini Flash.

        Args:
            prompt: The input prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            Generated text string.

        Raises:
            LLMTimeoutError: If generation exceeds 30 seconds.
            LLMError: For other generation failures.
        """
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise LLMError(
                "GOOGLE_CLOUD_PROJECT env var not set; cannot initialize Vertex AI client"
            )

        try:
            # Placeholder for actual implementation
            # In real scenario, would call google.cloud.aiplatform.generative_models
            raise NotImplementedError(
                "Vertex AI Gemini Flash implementation pending (requires google-cloud-aiplatform)"
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini Flash timeout: {e}") from e
        except Exception as e:
            raise LLMError(f"Gemini Flash generation failed: {e}") from e

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON output using Gemini Flash.

        Args:
            prompt: The input prompt.
            schema: JSON Schema dict the output must conform to.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            Parsed dict conforming to schema.

        Raises:
            LLMTimeoutError: If generation exceeds 30 seconds.
            LLMError: For other failures.
        """
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise LLMError("GOOGLE_CLOUD_PROJECT env var not set")

        try:
            # Placeholder for actual implementation
            raise NotImplementedError("Vertex AI Gemini Flash structured output pending")
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini Flash timeout: {e}") from e
        except Exception as e:
            raise LLMError(f"Gemini Flash structured output failed: {e}") from e


class VertexGeminiPro(LLMPort):
    """Vertex AI Gemini 2.5 Pro adapter (LLMPort implementation)."""

    MODEL: str = "gemini-2.5-pro"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Generate text using Gemini Pro.

        Args:
            prompt: The input prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            Generated text string.

        Raises:
            LLMTimeoutError: If generation exceeds 30 seconds.
            LLMError: For other generation failures.
        """
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise LLMError(
                "GOOGLE_CLOUD_PROJECT env var not set; cannot initialize Vertex AI client"
            )

        try:
            # Placeholder for actual implementation
            raise NotImplementedError(
                "Vertex AI Gemini Pro implementation pending (requires google-cloud-aiplatform)"
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini Pro timeout: {e}") from e
        except Exception as e:
            raise LLMError(f"Gemini Pro generation failed: {e}") from e

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON output using Gemini Pro.

        Args:
            prompt: The input prompt.
            schema: JSON Schema dict the output must conform to.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            Parsed dict conforming to schema.

        Raises:
            LLMTimeoutError: If generation exceeds 30 seconds.
            LLMError: For other failures.
        """
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise LLMError("GOOGLE_CLOUD_PROJECT env var not set")

        try:
            # Placeholder for actual implementation
            raise NotImplementedError("Vertex AI Gemini Pro structured output pending")
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini Pro timeout: {e}") from e
        except Exception as e:
            raise LLMError(f"Gemini Pro structured output failed: {e}") from e
