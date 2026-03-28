"""Vertex AI embedding adapter — real implementation of EmbeddingPort.

Uses text-embedding-005 model (768 dimensions) via google-cloud-aiplatform.

Falls back to NullEmbeddingAdapter when GOOGLE_CLOUD_PROJECT is not set,
so the API can run locally without GCP credentials (embeddings will be None).
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# No cross-package imports needed here — this is a pure infrastructure adapter


class VertexAIEmbedding:
    """Vertex AI text-embedding-005 adapter (768-dimensional embeddings).

    Lazy-initializes the Vertex AI client on first call to avoid startup
    failures when credentials aren't available (e.g. local dev without GCP).
    """

    MODEL = "text-embedding-005"

    def __init__(self, project_id: str, location: str = "us-central1") -> None:
        self._project_id = project_id
        self._location = location
        self._model = None

    def _get_model(self):  # type: ignore[no-untyped-def]
        """Lazy-initialize the Vertex AI embedding model."""
        if self._model is None:
            import vertexai  # type: ignore[import]
            from vertexai.language_models import TextEmbeddingModel  # type: ignore[import]

            vertexai.init(project=self._project_id, location=self._location)
            self._model = TextEmbeddingModel.from_pretrained(self.MODEL)
        return self._model

    async def embed(self, text: str) -> list[float]:
        """Generate 768-dimensional embedding for the given text.

        Runs the synchronous Vertex AI SDK in a thread pool executor to avoid
        blocking the async event loop.

        Args:
            text: Input text to embed.

        Returns:
            List of 768 floats (cosine-normalized).

        Raises:
            RuntimeError: If Vertex AI SDK is not installed or credentials are missing.
        """
        model = self._get_model()
        loop = asyncio.get_event_loop()

        def _call_vertex() -> list[float]:
            embeddings = model.get_embeddings([text])
            return list(embeddings[0].values)

        return await loop.run_in_executor(None, _call_vertex)


class NullEmbeddingAdapter:
    """No-op embedding adapter for local development without GCP credentials.

    Returns an empty list, meaning incidents will be stored without embeddings
    and semantic search will return no results.
    """

    async def embed(self, text: str) -> list[float]:
        """Return empty list — no embedding generated."""
        logger.warning(
            "NullEmbeddingAdapter: GOOGLE_CLOUD_PROJECT not set. "
            "Incident will be stored without embedding. "
            "Semantic search will not work until GCP credentials are configured."
        )
        return []


def make_embedding_adapter(
    project_id: str | None,
    location: str = "us-central1",
) -> VertexAIEmbedding | NullEmbeddingAdapter:
    """Factory: returns real Vertex adapter if GCP is configured, null otherwise."""
    if project_id:
        return VertexAIEmbedding(project_id=project_id, location=location)
    return NullEmbeddingAdapter()
