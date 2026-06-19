"""Section 3a: top-K retrieval from Chroma.

Pure function over the collection. Both the FastAPI ``/search`` endpoint and the
eval harness call this directly — no transport-layer logic here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from lac_ai.config import settings
from lac_ai.embed import get_collection
from lac_ai.embedders import Embedder, SentenceTransformerEmbedder


@dataclass(frozen=True)
class Hit:
    doc_id: str
    title: str
    text: str
    url: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def search(
    query: str,
    k: int | None = None,
    embedder: Embedder | None = None,
) -> list[Hit]:
    """Embed ``query`` and return the top-K hits.

    ``score`` is ``1 - distance`` for Chroma's cosine space, so higher = closer.
    """
    if not query.strip():
        return []
    k = k or settings.top_k
    embedder = embedder or SentenceTransformerEmbedder()
    collection = get_collection()

    vec = embedder.embed([query])[0]
    res = collection.query(
        query_embeddings=[vec],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    if not res["ids"] or not res["ids"][0]:
        return []

    hits: list[Hit] = []
    for _id, doc, meta, dist in zip(
        res["ids"][0],
        res["documents"][0],
        res["metadatas"][0],
        res["distances"][0],
        strict=False,
    ):
        hits.append(
            Hit(
                doc_id=meta["doc_id"],
                title=meta["title"],
                text=doc,
                url=meta["url"],
                score=1.0 - float(dist),
            )
        )
    return hits
