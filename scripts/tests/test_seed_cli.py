"""Integration tests for seed-knowledge-base.py CLI.

Tests verify:
- CLI ingests incidents from URL (HTML + metadata extraction via LLM)
- CLI ingests incidents from JSONL file
- --auto-approve skips manual review step
- --dry-run shows what would be ingested without persisting
- Generated embeddings are valid 768-dim vectors
- Database is populated with incidents

Requires: GOOGLE_CLOUD_PROJECT for LLM extraction, test PostgreSQL database.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestSeedCLI:
    """Integration tests for seed-knowledge-base.py CLI."""

    async def test_ingest_from_url_creates_incident(self) -> None:
        """Test that CLI can ingest incident from URL."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_ingest_from_jsonl_file_creates_multiple_incidents(self) -> None:
        """Test that CLI can ingest multiple incidents from JSONL file."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_auto_approve_flag_skips_confirmation(self) -> None:
        """Test that --auto-approve flag bypasses manual review step."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_dry_run_does_not_persist_to_database(self) -> None:
        """Test that --dry-run shows incidents without persisting."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_ingested_incidents_have_embeddings(self) -> None:
        """Test that ingested incidents have valid 768-dim embeddings."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_ingested_incidents_appear_in_database(self) -> None:
        """Test that incidents are persisted and retrievable from database."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_cli_handles_invalid_url_gracefully(self) -> None:
        """Test that CLI handles unreachable URLs without crashing."""
        pytest.skip("seed-knowledge-base.py not yet implemented")

    async def test_cli_extracts_metadata_via_llm(self) -> None:
        """Test that CLI uses LLM to extract incident metadata from HTML."""
        pytest.skip("seed-knowledge-base.py not yet implemented")
