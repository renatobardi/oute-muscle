"""RAG Pipeline — transforms code diff into advisory via LLM.

Constitution IV: RAG = Retrieve → Augment → Generate
Pipeline steps:
  1. Truncate diff to 3000 lines
  2. Embed the diff text (Vertex AI text-embedding-005)
  3. Vector search for similar incidents (pgvector)
  4. Build prompt with incident context
  5. Generate advisory via LLM Router
  6. Return Advisory entity

Confidence scoring:
  - If incidents found: min(0.9, 0.5 + 0.1 * count)
  - If no incidents: 0.3
"""

from __future__ import annotations

import uuid

from ...ports.embedding import EmbeddingPort
from ...ports.vector_search import VectorSearchPort
from ..incidents.enums import RiskLevel
from ..scanning.entities import Advisory
from .diff_processor import truncate_diff
from .llm_router import LLMRouter


class RAGPipeline:
    """Orchestrates the RAG flow: embedding → search → LLM → advisory."""

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_search_port: VectorSearchPort,
        llm_router: LLMRouter,
    ) -> None:
        """Initialize RAG pipeline with ports.

        Args:
            embedding_port: Adapter for generating embeddings.
            vector_search_port: Adapter for vector similarity search.
            llm_router: Router for model selection.
        """
        self.embedding_port = embedding_port
        self.vector_search_port = vector_search_port
        self.llm_router = llm_router

    async def process(
        self,
        diff: str,
        *,
        tenant_id: uuid.UUID,
        risk_level: RiskLevel,
        scan_id: uuid.UUID | None = None,
    ) -> Advisory:
        """Process a code diff into an advisory.

        Args:
            diff: Unified diff text from code changes.
            tenant_id: Tenant ID for search filtering.
            risk_level: Computed risk level from Layer 1 findings.
            scan_id: Optional scan ID to link advisory to.

        Returns:
            Advisory entity with text, confidence, and incident refs.
        """
        # Step 1: Truncate diff if needed
        processed_diff, was_truncated = truncate_diff(diff)

        # Step 2: Embed the diff
        diff_embedding = await self.embedding_port.embed(processed_diff)

        # Step 3: Vector search for similar incidents
        similar_results = await self.vector_search_port.find_similar(
            diff_embedding,
            tenant_id=tenant_id,
            limit=5,
            min_similarity=0.7,
        )

        # Step 4: Build prompt with incident context
        incidents = [result.incident for result in similar_results]
        prompt = self._build_prompt(processed_diff, incidents, was_truncated)

        # Step 5: Generate advisory via LLM Router
        advisory_text = await self.llm_router.generate(prompt, risk_level)

        # Step 6: Calculate confidence
        confidence = self._calculate_confidence(len(incidents))

        # Step 7: Build Advisory entity
        incident_id = (
            incidents[0].id if incidents else uuid.uuid4()
        )  # Use first incident or generate placeholder

        advisory = Advisory(
            scan_id=scan_id or uuid.uuid4(),
            tenant_id=tenant_id,
            incident_id=incident_id,
            confidence_score=confidence,
            risk_level=risk_level,
            matched_anti_pattern=self._extract_anti_pattern(incidents),
            analysis_text=advisory_text,
            llm_model_used=self._get_model_name(risk_level),
        )

        return advisory

    def _build_prompt(self, diff: str, incidents: list, was_truncated: bool) -> str:
        """Build LLM prompt with diff and incident context.

        Args:
            diff: Processed diff text.
            incidents: Related incidents from vector search.
            was_truncated: Whether diff was truncated.

        Returns:
            Formatted prompt for LLM.
        """
        prompt = (
            "You are a security code analysis assistant. "
            "Analyze the following code diff and provide security advisory.\n\n"
        )

        if was_truncated:
            prompt += (
                "[Note: This diff was truncated at 3000 lines. The full change may be larger.]\n\n"
            )

        prompt += f"Code Diff:\n```\n{diff}\n```\n\n"

        if incidents:
            prompt += "Similar Past Incidents:\n"
            for incident in incidents:
                prompt += (
                    f"- {incident.title}\n"
                    f"  Category: {incident.category}\n"
                    f"  Anti-Pattern: {incident.anti_pattern}\n"
                    f"  Remediation: {incident.remediation}\n\n"
                )
        else:
            prompt += (
                "No similar incidents found in the knowledge base. "
                "Provide a generic security analysis.\n\n"
            )

        prompt += (
            "Provide:\n"
            "1. Security risk assessment\n"
            "2. Specific code locations of concern\n"
            "3. Recommended fixes\n"
            "4. References to the similar incidents (if any)\n"
        )

        return prompt

    def _calculate_confidence(self, incident_count: int) -> float:
        """Calculate confidence score based on incident matches.

        Args:
            incident_count: Number of similar incidents found.

        Returns:
            Confidence score 0.0-1.0.
        """
        if incident_count > 0:
            # Higher confidence with more incident matches
            # Formula: min(0.9, 0.5 + 0.1 * count)
            return min(0.9, 0.5 + 0.1 * incident_count)
        else:
            # Low confidence when no incidents found
            return 0.3

    def _extract_anti_pattern(self, incidents: list) -> str:
        """Extract first incident's anti-pattern, or return generic.

        Args:
            incidents: Related incidents.

        Returns:
            Anti-pattern string.
        """
        if incidents:
            return incidents[0].anti_pattern
        return "Unidentified security pattern"

    def _get_model_name(self, risk_level: RiskLevel) -> str:
        """Determine which model name based on risk level.

        Args:
            risk_level: The risk level.

        Returns:
            Model identifier string.
        """
        if risk_level == RiskLevel.LOW:
            return "gemini-2.5-flash"
        elif risk_level == RiskLevel.MEDIUM:
            return "gemini-2.5-pro"
        else:  # HIGH
            return "claude-sonnet-4@20251101"
