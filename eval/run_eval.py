"""Retrieval-quality evaluation harness.

Loads hand-labeled queries from ``eval/queries.json`` and runs each one through
``lac_ai.retrieve.search`` against the live Chroma index. Reports per-query
Recall@K and Reciprocal Rank, plus the aggregate **Recall@K** and **MRR**.

Run from the project root:

    uv run python eval/run_eval.py
    uv run python eval/run_eval.py --k 5 --out eval/results.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lac_ai.config import settings
from lac_ai.embedders import SentenceTransformerEmbedder
from lac_ai.retrieve import search

EVAL_DIR = Path(__file__).resolve().parent
QUERIES_PATH = EVAL_DIR / "queries.json"


def reciprocal_rank(hit_ids: list[str], relevant: set[str]) -> float:
    for i, doc_id in enumerate(hit_ids, start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def recall_at_k(hit_ids: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    return len(set(hit_ids) & relevant) / len(relevant)


def evaluate(k: int) -> dict:
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))["queries"]
    embedder = SentenceTransformerEmbedder()

    rows = []
    for q in queries:
        hits = search(q["query"], k=k, embedder=embedder)
        hit_ids = [h.doc_id for h in hits]
        relevant = set(q["relevant_doc_ids"])

        r_at_k = recall_at_k(hit_ids, relevant)
        rr = reciprocal_rank(hit_ids, relevant)
        rank_of_first = next((i for i, hid in enumerate(hit_ids, 1) if hid in relevant), None)

        rows.append(
            {
                "id": q["id"],
                "query": q["query"],
                "relevant": sorted(relevant),
                "top_hits": [
                    {"doc_id": h.doc_id, "title": h.title, "score": round(h.score, 3)}
                    for h in hits
                ],
                "rank_of_first_relevant": rank_of_first,
                "recall_at_k": r_at_k,
                "reciprocal_rank": rr,
            }
        )

    n = len(rows)
    mean_recall = sum(r["recall_at_k"] for r in rows) / n if n else 0.0
    mrr = sum(r["reciprocal_rank"] for r in rows) / n if n else 0.0

    return {
        "k": k,
        "embedding_model": settings.embedding_model,
        "n_queries": n,
        "aggregate": {"recall_at_k": mean_recall, "mrr": mrr},
        "rows": rows,
    }


def format_markdown(result: dict) -> str:
    k = result["k"]
    agg = result["aggregate"]
    lines = [
        "# Retrieval evaluation",
        "",
        f"- Embedding model: `{result['embedding_model']}`",
        f"- Queries: {result['n_queries']}",
        f"- K: {k}",
        "",
        "## Aggregate",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Recall@{k} | **{agg['recall_at_k']:.3f}** |",
        f"| MRR | **{agg['mrr']:.3f}** |",
        "",
        "## Per-query",
        "",
        f"| Query | Relevant | Rank of first relevant | Recall@{k} | RR |",
        "|---|---|---|---|---|",
    ]
    for r in result["rows"]:
        rank = r["rank_of_first_relevant"]
        rank_str = str(rank) if rank is not None else "—"
        relevant = ", ".join(r["relevant"])
        lines.append(
            f"| {r['query']} | `{relevant}` | {rank_str} | "
            f"{r['recall_at_k']:.3f} | {r['reciprocal_rank']:.3f} |"
        )

    lines += ["", "## Top hits per query", ""]
    for r in result["rows"]:
        lines.append(f"### {r['query']}")
        lines.append("")
        lines.append(f"Relevant: `{', '.join(r['relevant'])}`")
        lines.append("")
        lines.append("| Rank | Score | doc_id | Title |")
        lines.append("|---|---|---|---|")
        for i, h in enumerate(r["top_hits"], 1):
            marker = " (*)" if h["doc_id"] in r["relevant"] else ""
            lines.append(
                f"| {i} | {h['score']:.3f} | `{h['doc_id']}`{marker} | {h['title']} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=settings.top_k)
    parser.add_argument(
        "--out", type=Path, default=None, help="Optional markdown output path."
    )
    args = parser.parse_args()

    result = evaluate(args.k)
    md = format_markdown(result)
    print(md)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"\nWrote {args.out}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
