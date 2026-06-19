"""Section 2: pluggable text chunker.

Default is whole-document — one chunk per Wikipedia summary, so retrieval hits
map 1:1 to articles and citation is trivial. Swap in a sentence/paragraph chunker
by passing a different ``Chunker`` to :func:`lac_ai.embed.build_index`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    url: str


@dataclass(frozen=True)
class SourceDoc:
    """Minimal view of a raw doc from corpus.jsonl that chunkers need."""

    id: str
    title: str
    text: str
    url: str


Chunker = Callable[[SourceDoc], list[Chunk]]


def whole_doc(doc: SourceDoc) -> list[Chunk]:
    """Default chunker: emit a single chunk per doc."""
    return [
        Chunk(
            chunk_id=doc.id,
            doc_id=doc.id,
            title=doc.title,
            text=doc.text,
            url=doc.url,
        )
    ]
