"""Integration tests for embedding generation on incident create/update.

Tests verify:
- Incident created without embedding gets embedded before persistence
- Incident updated with changed content gets re-embedded
- Embedding has correct dimensions (768 for text-embedding-005)
- Embedding is stored and retrieved from database

Requires: GOOGLE_CLOUD_PROJECT and Vertex AI credentials for embedding calls.
"""

from __future__ import annotations

import pytest
from src.domain.incidents.entity import Incident

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestEmbeddingService:
    """Integration tests for Vertex AI embedding adapter."""

    async def test_incident_created_without_embedding_gets_embedded(
        self, sample_incident: Incident
    ) -> None:
        """Test that incident without embedding gets embedded before DB persistence."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")

    async def test_embedding_has_correct_dimensions(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test that embedding has exactly 768 dimensions."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")

    async def test_embedding_generated_from_title_and_anti_pattern(
        self, sample_incident: Incident
    ) -> None:
        """Test that embedding combines title and anti_pattern for semantic meaning."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")

    async def test_incident_update_re_generates_embedding(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test that updating incident anti_pattern triggers re-embedding."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")

    async def test_embedding_retrieval_from_database(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test that embedding is correctly stored in and retrieved from pgvector."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")

    async def test_embedding_handles_long_text(
        self, sample_incident_with_embedding: Incident
    ) -> None:
        """Test that embedding works with long incident descriptions."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")

    async def test_embedding_consistency_for_same_input(self, sample_incident: Incident) -> None:
        """Test that same incident text always produces same embedding."""
        pytest.skip("Vertex AI embedding adapter not yet implemented")
