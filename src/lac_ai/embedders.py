"""Section 2: Embedder protocol + the local sentence-transformers implementation.

Anything that exposes :meth:`embed` and a :attr:`model_id` works — so swapping to
Voyage / OpenAI / a code-aware embedder is a one-file change (write a new class,
pass it to :func:`lac_ai.embed.build_index`).
"""

from __future__ import annotations

from typing import Protocol

from lac_ai.config import settings


class Embedder(Protocol):
    model_id: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Local sentence-transformers embedder. Loads the model lazily on first use."""

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or settings.embedding_model
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_id)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure_loaded()
        assert self._model is not None
        vectors = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]
