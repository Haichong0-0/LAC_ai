"""One-off retrieval sanity check. Not part of the package surface."""

from __future__ import annotations

from lac_ai.embed import get_collection
from lac_ai.embedders import SentenceTransformerEmbedder

QUERIES = [
    "Who invented the C programming language?",
    "functional language with strong static typing",
    "language used for scientific computing on the JVM",
]


def main() -> None:
    coll = get_collection()
    embedder = SentenceTransformerEmbedder()
    for q in QUERIES:
        vec = embedder.embed([q])[0]
        res = coll.query(
            query_embeddings=[vec],
            n_results=5,
            include=["metadatas", "distances"],
        )
        print(f"\nQ: {q}")
        for dist, meta in zip(res["distances"][0], res["metadatas"][0], strict=False):
            print(f"  {dist:.3f}  {meta['title']}")


if __name__ == "__main__":
    main()
