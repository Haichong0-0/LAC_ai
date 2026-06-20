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
    """Local sentence-transformers embedder.

    Models are cached at the class level by id, so constructing a fresh
    ``SentenceTransformerEmbedder(...)`` for the same model is effectively free
    after the first one. Without this, a long-running FastAPI server would
    reload weights on every request.
    """

    _MODEL_CACHE: dict[str, object] = {}

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or settings.embedding_model
        self._model = self._MODEL_CACHE.get(self.model_id)

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.model_id)
            self._MODEL_CACHE[self.model_id] = model
            self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure_loaded()
        assert self._model is not None
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]


def get_default_embedder() -> SentenceTransformerEmbedder:
    """Eagerly-loaded default embedder, suitable for FastAPI lifespan pre-warm."""
    embedder = SentenceTransformerEmbedder()
    embedder._ensure_loaded()
    return embedder
