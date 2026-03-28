"""LLM port — abstracts Vertex AI Gemini Flash/Pro and Claude Sonnet 4.

Constitution V: All LLM access via Vertex AI. Three models:
  - Gemini 2.5 Flash (~70% traffic, fast triage)
  - Gemini 2.5 Pro (~15% traffic, medium complexity)
  - Claude Sonnet 4 (~15% traffic, high-risk deep analysis)

Routing is deterministic based on risk score, not random.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMPort(Protocol):
    """Port for LLM text generation. Implemented by Vertex AI adapters."""

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The input prompt.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            Generated text string.

        Raises:
            LLMTimeoutError: If generation exceeds 30 seconds (Constitution V).
            LLMError: For other generation failures.
        """
        ...

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON output conforming to a schema.

        Args:
            prompt: The input prompt.
            schema: JSON Schema dict the output must conform to.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.

        Returns:
            Parsed dict conforming to the provided schema.

        Raises:
            LLMTimeoutError: If generation exceeds 30 seconds.
            LLMStructuredOutputError: If output cannot be parsed to schema.
            LLMError: For other generation failures.
        """
        ...


class LLMError(Exception):
    """Base error for LLM port failures."""


class LLMTimeoutError(LLMError):
    """Raised when LLM generation exceeds the 30-second timeout."""


class LLMStructuredOutputError(LLMError):
    """Raised when structured output cannot be parsed to the required schema."""
