"""Shared pytest fixtures.

These fixtures isolate tests from the real on-disk Chroma store and the live
Anthropic API. Every test in this suite is offline and deterministic.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import chromadb
import pytest

from lac_ai import embed as embed_mod
from lac_ai import retrieve as retrieve_mod
from lac_ai.embedders import Embedder


class FakeEmbedder:
    """Deterministic toy embedder — 26-dim per-letter count vector.

    Real bag-of-characters cosine: queries that share letters with a document
    rank higher than ones that don't. Predictable for assertions.
    """

    model_id = "fake-embedder-v1"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            vec = [0.0] * 26
            for c in t.lower():
                if "a" <= c <= "z":
                    vec[ord(c) - ord("a")] += 1.0
            if all(v == 0.0 for v in vec):
                vec[0] = 1.0  # avoid zero vectors for cosine
            out.append(vec)
        return out


@pytest.fixture
def fake_embedder() -> Embedder:
    return FakeEmbedder()


@pytest.fixture
def tmp_chroma(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[chromadb.api.ClientAPI]:
    """Point the project's Chroma client at a tmp directory for one test."""
    from lac_ai.config import settings

    monkeypatch.setattr(settings, "chroma_dir", tmp_path / "chroma")
    monkeypatch.setattr(settings, "collection", "test_corpus")
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    yield client


@pytest.fixture
def seeded_collection(tmp_chroma: chromadb.api.ClientAPI, fake_embedder: Embedder):
    """Insert three toy docs into the tmp collection using the fake embedder."""
    collection = embed_mod.get_collection(client=tmp_chroma)
    docs = [
        ("apple", "Apple", "fruit red sweet apple", "http://x/apple"),
        ("banana", "Banana", "yellow tropical fruit banana", "http://x/banana"),
        ("carrot", "Carrot", "orange root vegetable carrot", "http://x/carrot"),
    ]
    texts = [d[2] for d in docs]
    vectors = fake_embedder.embed(texts)
    collection.upsert(
        ids=[d[0] for d in docs],
        embeddings=vectors,
        documents=texts,
        metadatas=[
            {
                "doc_id": d[0],
                "title": d[1],
                "url": d[3],
                "content_hash": "h",
                "embedder": fake_embedder.model_id,
            }
            for d in docs
        ],
    )
    return collection


@dataclass
class _Block:
    type: str
    text: str


@dataclass
class _Response:
    content: list[_Block]


class FakeAnthropic:
    """Drop-in stand-in for ``anthropic.Anthropic`` for tests.

    Returns whatever ``set_reply`` was called with, defaults to a cited stub.
    """

    def __init__(self, reply: str | None = None) -> None:
        self._reply = reply or "Stub answer [c_(programming_language)]."
        self.messages = self
        self.calls: list[dict] = []

    def set_reply(self, reply: str) -> None:
        self._reply = reply

    def create(self, **kwargs) -> _Response:  # noqa: D401  (mock signature)
        self.calls.append(kwargs)
        return _Response(content=[_Block(type="text", text=self._reply)])


@pytest.fixture
def fake_anthropic() -> FakeAnthropic:
    return FakeAnthropic()


@pytest.fixture(autouse=True)
def _stub_search_embedder(monkeypatch: pytest.MonkeyPatch, fake_embedder: Embedder) -> None:
    """Default ``search`` calls in every consuming module to the fake embedder.

    Each importer of ``retrieve.search`` (``generate``, ``api``) bound the name
    at import time, so patching only ``retrieve.search`` would not reach them.
    We patch all three bindings.
    """
    from lac_ai import api as api_mod
    from lac_ai import generate as generate_mod

    real_search = retrieve_mod.search

    def patched(query: str, k: int | None = None, embedder=None):
        return real_search(query, k=k, embedder=embedder or fake_embedder)

    monkeypatch.setattr(retrieve_mod, "search", patched)
    monkeypatch.setattr(generate_mod, "search", patched)
    monkeypatch.setattr(api_mod, "search_core", patched)
