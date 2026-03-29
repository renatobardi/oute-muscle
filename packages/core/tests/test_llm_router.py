"""Unit tests for LLM Router — deterministic routing based on risk score.

Constitution V: Router selects LLM model based on risk level.
Fallback chain on LLMTimeoutError: Flash → Pro → Claude
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from packages.core.src.domain.incidents.enums import RiskLevel
from packages.core.src.ports.llm import LLMPort, LLMTimeoutError


class TestLLMRouter:
    """Test suite for LLM Router routing logic and fallbacks."""

    @pytest.mark.asyncio
    async def test_low_risk_routes_to_flash(self) -> None:
        """Risk score LOW should use Gemini Flash."""
        flash = AsyncMock(spec=LLMPort)
        flash.generate = AsyncMock(return_value="Flash response")
        pro = AsyncMock(spec=LLMPort)
        claude = AsyncMock(spec=LLMPort)

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)
        result = await router.generate("test prompt", RiskLevel.LOW)

        assert result == "Flash response"
        flash.generate.assert_called_once()
        pro.generate.assert_not_called()
        claude.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_medium_risk_routes_to_pro(self) -> None:
        """Risk score MEDIUM should use Gemini Pro."""
        flash = AsyncMock(spec=LLMPort)
        pro = AsyncMock(spec=LLMPort)
        pro.generate = AsyncMock(return_value="Pro response")
        claude = AsyncMock(spec=LLMPort)

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)
        result = await router.generate("test prompt", RiskLevel.MEDIUM)

        assert result == "Pro response"
        flash.generate.assert_not_called()
        pro.generate.assert_called_once()
        claude.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_high_risk_routes_to_claude(self) -> None:
        """Risk score HIGH should use Claude Sonnet 4."""
        flash = AsyncMock(spec=LLMPort)
        pro = AsyncMock(spec=LLMPort)
        claude = AsyncMock(spec=LLMPort)
        claude.generate = AsyncMock(return_value="Claude response")

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)
        result = await router.generate("test prompt", RiskLevel.HIGH)

        assert result == "Claude response"
        flash.generate.assert_not_called()
        pro.generate.assert_not_called()
        claude.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_flash_to_pro_on_timeout(self) -> None:
        """Flash timeout should retry with Pro."""
        flash = AsyncMock(spec=LLMPort)
        flash.generate = AsyncMock(side_effect=LLMTimeoutError("timeout"))
        pro = AsyncMock(spec=LLMPort)
        pro.generate = AsyncMock(return_value="Pro fallback")
        claude = AsyncMock(spec=LLMPort)

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)
        result = await router.generate("test prompt", RiskLevel.LOW)

        assert result == "Pro fallback"
        flash.generate.assert_called_once()
        pro.generate.assert_called_once()
        claude.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_pro_to_claude_on_timeout(self) -> None:
        """Pro timeout should retry with Claude."""
        flash = AsyncMock(spec=LLMPort)
        pro = AsyncMock(spec=LLMPort)
        pro.generate = AsyncMock(side_effect=LLMTimeoutError("timeout"))
        claude = AsyncMock(spec=LLMPort)
        claude.generate = AsyncMock(return_value="Claude fallback")

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)
        result = await router.generate("test prompt", RiskLevel.MEDIUM)

        assert result == "Claude fallback"
        pro.generate.assert_called_once()
        claude.generate.assert_called_once()
        flash.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_exhausted_raises(self) -> None:
        """All three models timeout should raise LLMTimeoutError."""
        flash = AsyncMock(spec=LLMPort)
        flash.generate = AsyncMock(side_effect=LLMTimeoutError("timeout"))
        pro = AsyncMock(spec=LLMPort)
        pro.generate = AsyncMock(side_effect=LLMTimeoutError("timeout"))
        claude = AsyncMock(spec=LLMPort)
        claude.generate = AsyncMock(side_effect=LLMTimeoutError("timeout"))

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)

        with pytest.raises(LLMTimeoutError):
            await router.generate("test prompt", RiskLevel.HIGH)

    @pytest.mark.asyncio
    async def test_router_returns_advisory_text(self) -> None:
        """Happy path: router returns string from chosen model."""
        flash = AsyncMock(spec=LLMPort)
        flash.generate = AsyncMock(return_value="Generated advisory text")
        pro = AsyncMock(spec=LLMPort)
        claude = AsyncMock(spec=LLMPort)

        from packages.core.src.domain.advisory.llm_router import LLMRouter

        router = LLMRouter(flash=flash, pro=pro, claude=claude)
        result = await router.generate("test prompt", RiskLevel.LOW)

        assert isinstance(result, str)
        assert len(result) > 0
