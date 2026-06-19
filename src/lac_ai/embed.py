"""Section 2: build the vector index.

Pipeline: read ``corpus.jsonl`` → normalize → chunk → embed → upsert into Chroma.

Idempotent: each chunk stores a content hash in Chroma metadata; on re-run we
only re-embed chunks whose hash changed. Lets you re-embed after a corpus refresh
without paying for the unchanged majority.

This section owns *all* text decisions (normalization, chunking, embedder choice).
Section 1 (ingestion) is strictly a byte-for-byte fetch.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import chromadb

from lac_ai.chunking import Chunk, Chunker, SourceDoc, whole_doc
from lac_ai.config import settings
from lac_ai.embedders import Embedder, SentenceTransformerEmbedder

_CITATION_MARKER_RE = re.compile(r"\[\d+\]")
_WS_RE = re.compile(r"[ \t]+")


def normalize(text: str) -> str:
    """Light normalization: NFC unicode, strip ``[1]``-style citation markers, collapse ws."""
    text = unicodedata.normalize("NFC", text)
    text = _CITATION_MARKER_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def _read_corpus(path: Path) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        docs.append(SourceDoc(id=d["id"], title=d["title"], text=d["text"], url=d["url"]))
    return docs


def _chunk_hash(chunk: Chunk, model_id: str) -> str:
    h = hashlib.sha256()
    h.update(model_id.encode("utf-8"))
    h.update(b"\0")
    h.update(chunk.text.encode("utf-8"))
    return h.hexdigest()


def get_collection(client: chromadb.api.ClientAPI | None = None) -> chromadb.api.models.Collection.Collection:
    """Get-or-create the project's Chroma collection."""
    client = client or chromadb.PersistentClient(path=str(settings.chroma_dir))
    return client.get_or_create_collection(
        name=settings.collection,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(
    corpus_path: Path | None = None,
    embedder: Embedder | None = None,
    chunker: Chunker = whole_doc,
) -> dict[str, int]:
    """Embed the corpus into Chroma. Returns ``{processed, upserted, skipped}``."""
    corpus_path = corpus_path or settings.corpus_path
    embedder = embedder or SentenceTransformerEmbedder()

    docs = _read_corpus(corpus_path)
    collection = get_collection()

    chunks: list[Chunk] = []
    for d in docs:
        normalized = SourceDoc(id=d.id, title=d.title, text=normalize(d.text), url=d.url)
        chunks.extend(chunker(normalized))

    existing = collection.get(ids=[c.chunk_id for c in chunks], include=["metadatas"])
    existing_hash: dict[str, str] = {}
    for cid, meta in zip(existing["ids"], existing["metadatas"], strict=False):
        if meta and "content_hash" in meta:
            existing_hash[cid] = meta["content_hash"]

    to_embed: list[Chunk] = []
    hashes: dict[str, str] = {}
    for c in chunks:
        h = _chunk_hash(c, embedder.model_id)
        hashes[c.chunk_id] = h
        if existing_hash.get(c.chunk_id) != h:
            to_embed.append(c)

    if to_embed:
        vectors = embedder.embed([c.text for c in to_embed])
        collection.upsert(
            ids=[c.chunk_id for c in to_embed],
            embeddings=vectors,
            documents=[c.text for c in to_embed],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "url": c.url,
                    "content_hash": hashes[c.chunk_id],
                    "embedder": embedder.model_id,
                }
                for c in to_embed
            ],
        )

    return {
        "processed": len(chunks),
        "upserted": len(to_embed),
        "skipped": len(chunks) - len(to_embed),
    }
