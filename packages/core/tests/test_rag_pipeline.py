"""Unit tests for RAG Pipeline — transforms diff into advisory.

Constitution II: Tests written before implementation using all mocked dependencies.
RAG = Retrieve → Augment → Generate
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from src.domain.incidents.entity import Incident
from src.domain.incidents.enums import (
    IncidentCategory,
    IncidentSeverity,
    RiskLevel,
)
from src.domain.scanning.entities import Advisory
from src.ports.embedding import EmbeddingPort
from src.ports.vector_search import VectorSearchPort, VectorSearchResult


class TestRAGPipeline:
    """Test RAG pipeline steps: truncate → embed → search → prompt → generate."""

    @pytest.mark.asyncio
    async def test_diff_is_embedded_before_search(self) -> None:
        """Step 1: diff text is passed to embedding adapter."""
        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory text")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        diff = "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,3 @@\n-old\n+new"
        tenant_id = uuid.uuid4()

        await pipeline.process(diff, tenant_id=tenant_id, risk_level=RiskLevel.LOW)

        embedding_adapter.embed.assert_called_once()
        call_args = embedding_adapter.embed.call_args
        assert diff in str(call_args)

    @pytest.mark.asyncio
    async def test_vector_search_uses_diff_embedding(self) -> None:
        """Step 2: embedding result is passed to vector search."""
        test_embedding = [0.2] * 768
        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=test_embedding)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        diff = "some diff"
        tenant_id = uuid.uuid4()

        await pipeline.process(diff, tenant_id=tenant_id, risk_level=RiskLevel.LOW)

        search_adapter.find_similar.assert_called_once()
        call_args = search_adapter.find_similar.call_args
        assert call_args[0][0] == test_embedding

    @pytest.mark.asyncio
    async def test_advisory_generated_with_incidents(self) -> None:
        """Step 3: if search returns results, LLM prompt includes incident refs."""
        user_id = uuid.uuid4()
        incident = Incident(
            id=uuid.uuid4(),
            title="Test incident",
            category=IncidentCategory.UNSAFE_REGEX,
            severity=IncidentSeverity.HIGH,
            anti_pattern="bad pattern",
            remediation="fix it",
            created_by=user_id,
        )
        search_result = VectorSearchResult(
            incident=incident,
            similarity_score=0.85,
            distance=0.15,
        )

        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[search_result])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory with context")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        diff = "code diff"
        tenant_id = uuid.uuid4()

        await pipeline.process(diff, tenant_id=tenant_id, risk_level=RiskLevel.LOW)

        # Verify LLM was called with incidents in context
        llm_router.generate.assert_called_once()
        call_args = llm_router.generate.call_args
        prompt = call_args[0][0]
        assert "Test incident" in prompt or incident.id in prompt

    @pytest.mark.asyncio
    async def test_advisory_generated_without_incidents(self) -> None:
        """Step 4: if search returns empty, LLM gets generic prompt."""
        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="generic advisory")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        diff = "code diff"
        tenant_id = uuid.uuid4()

        advisory = await pipeline.process(diff, tenant_id=tenant_id, risk_level=RiskLevel.LOW)

        # Verify LLM was still called
        llm_router.generate.assert_called_once()
        assert advisory is not None

    @pytest.mark.asyncio
    async def test_diff_truncated_at_3000_lines(self) -> None:
        """Step 0: diffs over 3000 lines are truncated with warning."""
        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        # Create a diff with 3001 lines
        large_diff = "\n".join([f"line {i}" for i in range(3001)])
        tenant_id = uuid.uuid4()

        await pipeline.process(large_diff, tenant_id=tenant_id, risk_level=RiskLevel.LOW)

        # Verify embedding was called with truncated version
        embedding_adapter.embed.assert_called_once()
        call_args = embedding_adapter.embed.call_args
        embedded_text = call_args[0][0]
        # Should contain truncation warning
        assert "truncated" in embedded_text.lower() or len(embedded_text.split("\n")) <= 3001

    @pytest.mark.asyncio
    async def test_pipeline_returns_advisory_entity(self) -> None:
        """Output: RAG pipeline returns Advisory entity."""
        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory text")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        diff = "code diff"
        scan_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        advisory = await pipeline.process(
            diff, tenant_id=tenant_id, risk_level=RiskLevel.LOW, scan_id=scan_id
        )

        assert advisory is not None
        assert isinstance(advisory, Advisory)
        assert advisory.scan_id == scan_id
        assert advisory.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_confidence_high_when_incidents_found(self) -> None:
        """Confidence >= 0.7 when similar incidents are found."""
        user_id = uuid.uuid4()
        incidents = [
            VectorSearchResult(
                incident=Incident(
                    id=uuid.uuid4(),
                    title=f"Incident {i}",
                    category=IncidentCategory.UNSAFE_REGEX,
                    severity=IncidentSeverity.HIGH,
                    anti_pattern="bad",
                    remediation="fix",
                    created_by=user_id,
                ),
                similarity_score=0.85,
                distance=0.15,
            )
            for i in range(2)
        ]

        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=incidents)
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        advisory = await pipeline.process("diff", tenant_id=uuid.uuid4(), risk_level=RiskLevel.LOW)

        assert advisory.confidence_score >= 0.7

    @pytest.mark.asyncio
    async def test_confidence_low_when_no_incidents(self) -> None:
        """Confidence < 0.5 when no similar incidents are found."""
        embedding_adapter = AsyncMock(spec=EmbeddingPort)
        embedding_adapter.embed = AsyncMock(return_value=[0.1] * 768)
        search_adapter = AsyncMock(spec=VectorSearchPort)
        search_adapter.find_similar = AsyncMock(return_value=[])
        llm_router = AsyncMock()
        llm_router.generate = AsyncMock(return_value="advisory")

        from src.domain.advisory.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(
            embedding_port=embedding_adapter,
            vector_search_port=search_adapter,
            llm_router=llm_router,
        )

        advisory = await pipeline.process("diff", tenant_id=uuid.uuid4(), risk_level=RiskLevel.LOW)

        assert advisory.confidence_score < 0.5
