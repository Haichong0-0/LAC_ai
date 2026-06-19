"""One-off build-time utility: fetch Wikipedia category members and emit a pruned title list.

Run from the project root:

    python scripts/fetch_title_list.py

Writes ``data/title_list.json`` with up to ``TARGET_SIZE`` Wikipedia article titles
sampled deterministically from ``Category:Programming_languages``. The resulting JSON
is committed to the repo; ``ingest.py`` reads it at corpus build time.

The prune logic here is intentionally programmatic and conservative — anything obviously
non-language (lists, comparisons, disambiguation pages, the parent article itself).
Further hand-pruning belongs in a *separate* commit so the diff is auditable.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

CATEGORY = "Category:Programming_languages"
API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "Lac_ai/0.1 (https://github.com/Haichong0-0/Lac_ai; take-home RAG assignment)"
TARGET_SIZE = 100
FETCH_LIMIT = 500

DENY_PREFIXES = ("List of ", "Comparison of ", "Lists of ", "Outline of ", "Index of ")
DENY_SUBSTRINGS = ("(disambiguation)",)
DENY_EXACT = {
    "Programming language",  # the parent topic article — too generic, would dominate
    "History of programming languages",
    "Generational list of programming languages",
}
DENY_PATTERNS = (re.compile(r"^Category:"),)


def fetch_category_members(category: str, limit: int) -> list[dict]:
    """Page through MediaWiki ``categorymembers`` and return article-namespace members."""
    members: list[dict] = []
    cont: dict[str, str] = {}
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": min(500, limit - len(members)),
            "cmnamespace": "0",  # article namespace only
            "cmtype": "page",
            "format": "json",
            **cont,
        }
        resp = requests.get(
            API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        members.extend(payload["query"]["categorymembers"])
        if len(members) >= limit:
            break
        if "continue" not in payload:
            break
        cont = payload["continue"]
    return members


def keep(title: str) -> bool:
    if title in DENY_EXACT:
        return False
    if any(title.startswith(p) for p in DENY_PREFIXES):
        return False
    if any(s in title for s in DENY_SUBSTRINGS):
        return False
    if any(p.match(title) for p in DENY_PATTERNS):
        return False
    return True


def main() -> int:
    raw = fetch_category_members(CATEGORY, FETCH_LIMIT)
    print(f"Fetched {len(raw)} raw category members from {CATEGORY}", file=sys.stderr)

    kept = [m for m in raw if keep(m["title"])]
    kept.sort(key=lambda m: m["title"])
    trimmed = kept[:TARGET_SIZE]
    print(
        f"Kept {len(kept)} after programmatic prune; trimmed to {len(trimmed)} for the title list.",
        file=sys.stderr,
    )

    out_path = Path(__file__).resolve().parents[1] / "data" / "title_list.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "source": f"https://en.wikipedia.org/wiki/{CATEGORY.replace(' ', '_')}",
        "category": CATEGORY,
        "fetched_count": len(raw),
        "kept_after_prune": len(kept),
        "target_size": TARGET_SIZE,
        "titles": [{"title": m["title"], "pageid": m["pageid"]} for m in trimmed],
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(out_path.parents[1])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
