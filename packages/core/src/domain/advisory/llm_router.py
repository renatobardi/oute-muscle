"""LLM Router — deterministic routing based on risk score.

Constitution V: Router selects model based on risk level.
Routing rules:
  - RiskLevel.LOW    → Gemini Flash (primary)
  - RiskLevel.MEDIUM → Gemini Pro (primary)
  - RiskLevel.HIGH   → Claude Sonnet 4 (primary)

Fallback chain (on LLMTimeoutError):
  - Flash → Pro → Claude → raises LLMTimeoutError

30-second timeout is handled by each adapter.
Router orchestrates the fallback logic.
"""

from __future__ import annotations

from ...ports.llm import LLMPort, LLMTimeoutError
from ..incidents.enums import RiskLevel


class LLMRouter:
    """Routes generation requests to appropriate LLM based on risk level."""

    def __init__(
        self,
        flash: LLMPort,
        pro: LLMPort,
        claude: LLMPort,
    ) -> None:
        """Initialize router with three LLM adapters.

        Args:
            flash: Gemini Flash adapter (fast triage).
            pro: Gemini Pro adapter (medium complexity).
            claude: Claude Sonnet 4 adapter (high-risk analysis).
        """
        self.flash = flash
        self.pro = pro
        self.claude = claude

    async def generate(self, prompt: str, risk_level: RiskLevel) -> str:
        """Generate text, routing to appropriate model based on risk level.

        Primary model selection:
          - LOW    → Flash
          - MEDIUM → Pro
          - HIGH   → Claude

        Fallback chain on LLMTimeoutError:
          - Flash → Pro → Claude → raise

        Args:
            prompt: The input prompt.
            risk_level: Computed risk level from scan findings.

        Returns:
            Generated advisory text.

        Raises:
            LLMTimeoutError: If all three models timeout.
        """
        if risk_level == RiskLevel.LOW:
            return await self._try_with_fallback(
                primary=self.flash,
                fallback1=self.pro,
                fallback2=self.claude,
                prompt=prompt,
            )
        elif risk_level == RiskLevel.MEDIUM:
            return await self._try_with_fallback(
                primary=self.pro,
                fallback1=self.claude,
                fallback2=self.flash,
                prompt=prompt,
            )
        else:  # RiskLevel.HIGH
            return await self._try_with_fallback(
                primary=self.claude,
                fallback1=self.pro,
                fallback2=self.flash,
                prompt=prompt,
            )

    async def _try_with_fallback(
        self,
        primary: LLMPort,
        fallback1: LLMPort,
        fallback2: LLMPort,
        prompt: str,
    ) -> str:
        """Try primary, then fallback1, then fallback2 on timeout.

        Args:
            primary: First adapter to try.
            fallback1: Second adapter to try on timeout.
            fallback2: Third adapter to try on timeout.
            prompt: The input prompt.

        Returns:
            Generated text from whichever adapter succeeds.

        Raises:
            LLMTimeoutError: If all three timeout.
        """
        try:
            return await primary.generate(prompt)
        except LLMTimeoutError:
            pass

        try:
            return await fallback1.generate(prompt)
        except LLMTimeoutError:
            pass

        try:
            return await fallback2.generate(prompt)
        except LLMTimeoutError as e:
            raise LLMTimeoutError("All LLM models timed out") from e
