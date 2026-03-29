"""Vertex AI LLM adapters — Gemini Flash, Gemini Pro, and Claude Sonnet 4.

Constitution V: All LLM access via Vertex AI.
  - Gemini 2.5 Flash: fast triage (low risk)
  - Gemini 2.5 Pro: deeper analysis (medium risk)
  - Claude Sonnet 4: max quality (high risk)

30-second timeout per call (Constitution V).
Falls back to NullLLMAdapter when GOOGLE_CLOUD_PROJECT is not set.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class VertexGeminiFlash:
    """Vertex AI Gemini 2.5 Flash adapter — fast, low-cost triage."""

    MODEL = "gemini-2.5-flash-preview-04-17"
    TIMEOUT = 30.0

    def __init__(self, project_id: str, location: str = "us-central1") -> None:
        self._project_id = project_id
        self._location = location
        self._model = None

    def _get_model(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            import vertexai  # type: ignore[import]
            from vertexai.generative_models import GenerativeModel  # type: ignore[import]

            vertexai.init(project=self._project_id, location=self._location)
            self._model = GenerativeModel(self.MODEL)
        return self._model

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        from packages.core.src.ports.llm import LLMError, LLMTimeoutError

        model = self._get_model()
        loop = asyncio.get_event_loop()

        def _call() -> str:
            from vertexai.generative_models import GenerationConfig  # type: ignore[import]

            cfg = GenerationConfig(max_output_tokens=max_tokens, temperature=temperature)
            response = model.generate_content(prompt, generation_config=cfg)
            return response.text

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _call),
                timeout=self.TIMEOUT,
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini Flash timeout after {self.TIMEOUT}s") from e
        except Exception as e:
            raise LLMError(f"Gemini Flash error: {e}") from e

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        from packages.core.src.ports.llm import LLMError

        full_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON that conforms to this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )
        text = await self.generate(full_prompt, max_tokens=max_tokens, temperature=temperature)

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Gemini Flash returned invalid JSON: {e}\nRaw: {text[:500]}") from e


class VertexGeminiPro:
    """Vertex AI Gemini 2.5 Pro adapter — deeper analysis."""

    MODEL = "gemini-2.5-pro-preview-03-25"
    TIMEOUT = 30.0

    def __init__(self, project_id: str, location: str = "us-central1") -> None:
        self._project_id = project_id
        self._location = location
        self._model = None

    def _get_model(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            import vertexai  # type: ignore[import]
            from vertexai.generative_models import GenerativeModel  # type: ignore[import]

            vertexai.init(project=self._project_id, location=self._location)
            self._model = GenerativeModel(self.MODEL)
        return self._model

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        from packages.core.src.ports.llm import LLMError, LLMTimeoutError

        model = self._get_model()
        loop = asyncio.get_event_loop()

        def _call() -> str:
            from vertexai.generative_models import GenerationConfig  # type: ignore[import]

            cfg = GenerationConfig(max_output_tokens=max_tokens, temperature=temperature)
            return model.generate_content(prompt, generation_config=cfg).text

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _call),
                timeout=self.TIMEOUT,
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini Pro timeout after {self.TIMEOUT}s") from e
        except Exception as e:
            raise LLMError(f"Gemini Pro error: {e}") from e

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        from packages.core.src.ports.llm import LLMError

        full_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON that conforms to this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )
        text = await self.generate(full_prompt, max_tokens=max_tokens, temperature=temperature)
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Gemini Pro returned invalid JSON: {e}") from e


class VertexClaudeSonnet:
    """Vertex AI Claude Sonnet 4 adapter — max quality for high-risk diffs."""

    MODEL = "claude-sonnet-4@20250514"
    TIMEOUT = 30.0

    def __init__(self, project_id: str, location: str = "us-east5") -> None:
        # Claude on Vertex AI is only available in us-east5
        self._project_id = project_id
        self._location = location
        self._client = None

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            import anthropic  # type: ignore[import]

            self._client = anthropic.AnthropicVertex(
                project_id=self._project_id,
                region=self._location,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        from packages.core.src.ports.llm import LLMError, LLMTimeoutError

        client = self._get_client()
        loop = asyncio.get_event_loop()

        def _call() -> str:
            message = client.messages.create(
                model=self.MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text  # type: ignore[index]

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _call),
                timeout=self.TIMEOUT,
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Claude Sonnet timeout after {self.TIMEOUT}s") from e
        except Exception as e:
            raise LLMError(f"Claude Sonnet error: {e}") from e

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        from packages.core.src.ports.llm import LLMError

        full_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON conforming to this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )
        text = await self.generate(full_prompt, max_tokens=max_tokens, temperature=temperature)
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Claude Sonnet returned invalid JSON: {e}") from e


class NullLLMAdapter:
    """No-op LLM adapter for local dev without GCP credentials."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        logger.warning("NullLLMAdapter: GCP not configured. Returning empty response.")
        return ""

    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        logger.warning("NullLLMAdapter: GCP not configured. Returning empty dict.")
        return {}
