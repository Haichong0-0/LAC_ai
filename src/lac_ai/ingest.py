"""Section 1: ingestion.

Strict responsibility: pull raw Wikipedia summaries for every title in
``data/title_list.json`` and persist them, byte-for-byte as fetched, to
``data/corpus.jsonl``. No normalization, no chunking, no embedding — those
decisions belong to Section 2 so swapping any of them stays a one-section change.

Idempotent: each record carries a SHA-256 of its raw text; on re-run, titles whose
fetched text hash matches the existing record are skipped.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import wikipediaapi

from lac_ai.config import settings

USER_AGENT = "Lac_ai/0.1 (https://github.com/Haichong0-0/Lac_ai; take-home RAG assignment)"


@dataclass
class Doc:
    id: str
    title: str
    text: str
    url: str
    sha256: str
    fetched_at: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)


def _slug(title: str) -> str:
    return title.lower().replace(" ", "_").replace("/", "_")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_title_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["titles"]


def read_existing(path: Path) -> dict[str, Doc]:
    """Return {id: Doc} from an existing corpus file, or empty dict."""
    if not path.exists():
        return {}
    out: dict[str, Doc] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out[d["id"]] = Doc(**d)
    return out


def fetch_one(wiki: wikipediaapi.Wikipedia, title: str) -> Doc | None:
    page = wiki.page(title)
    if not page.exists():
        return None
    text = page.summary or ""
    if not text.strip():
        return None
    return Doc(
        id=_slug(title),
        title=title,
        text=text,
        url=page.fullurl,
        sha256=_hash(text),
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def ingest(
    title_list_path: Path | None = None,
    corpus_path: Path | None = None,
    titles_override: Iterable[str] | None = None,
) -> dict[str, int]:
    """Fetch summaries for every title and write/refresh corpus.jsonl.

    Returns a small stats dict (``fetched``, ``skipped``, ``missing``, ``total``).
    """
    title_list_path = title_list_path or settings.title_list
    corpus_path = corpus_path or settings.corpus_path
    corpus_path.parent.mkdir(parents=True, exist_ok=True)

    if titles_override is not None:
        titles = list(titles_override)
    else:
        titles = [t["title"] for t in load_title_list(title_list_path)]

    existing = read_existing(corpus_path)
    wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language="en")

    stats = {"fetched": 0, "skipped": 0, "missing": 0, "total": len(titles)}
    docs: dict[str, Doc] = dict(existing)

    for title in titles:
        slug = _slug(title)
        doc = fetch_one(wiki, title)
        if doc is None:
            stats["missing"] += 1
            print(f"  MISSING  {title}", file=sys.stderr)
            continue
        prior = existing.get(slug)
        if prior and prior.sha256 == doc.sha256:
            stats["skipped"] += 1
            continue
        docs[slug] = doc
        stats["fetched"] += 1

    with corpus_path.open("w", encoding="utf-8") as fh:
        for doc in docs.values():
            fh.write(doc.to_json() + "\n")

    return stats
