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
        is_negative = len(relevant) == 0

        r_at_k = recall_at_k(hit_ids, relevant) if not is_negative else None
        rr = reciprocal_rank(hit_ids, relevant) if not is_negative else None
        rank_of_first = next((i for i, hid in enumerate(hit_ids, 1) if hid in relevant), None)
        top1_score = hits[0].score if hits else None

        rows.append(
            {
                "id": q["id"],
                "query": q["query"],
                "relevant": sorted(relevant),
                "is_negative": is_negative,
                "top_hits": [{"doc_id": h.doc_id, "title": h.title, "score": round(h.score, 3)} for h in hits],
                "rank_of_first_relevant": rank_of_first,
                "recall_at_k": r_at_k,
                "reciprocal_rank": rr,
                "top1_score": round(top1_score, 3) if top1_score is not None else None,
            }
        )

    answerable = [r for r in rows if not r["is_negative"]]
    negatives = [r for r in rows if r["is_negative"]]
    n_ans = len(answerable)
    mean_recall = sum(r["recall_at_k"] for r in answerable) / n_ans if n_ans else 0.0
    mrr = sum(r["reciprocal_rank"] for r in answerable) / n_ans if n_ans else 0.0

    return {
        "k": k,
        "embedding_model": settings.embedding_model,
        "n_queries": len(rows),
        "n_answerable": n_ans,
        "n_negative": len(negatives),
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
        f"- Queries: {result['n_queries']} ({result['n_answerable']} answerable, {result['n_negative']} negative)",
        f"- K: {k}",
        "",
        "## Aggregate (answerable queries only)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Recall@{k} | **{agg['recall_at_k']:.3f}** |",
        f"| MRR | **{agg['mrr']:.3f}** |",
        "",
        "## Answerable queries",
        "",
        f"| Query | Relevant | Rank of first relevant | Recall@{k} | RR |",
        "|---|---|---|---|---|",
    ]
    for r in result["rows"]:
        if r["is_negative"]:
            continue
        rank = r["rank_of_first_relevant"]
        rank_str = str(rank) if rank is not None else "—"
        relevant = ", ".join(r["relevant"])
        lines.append(
            f"| {r['query']} | `{relevant}` | {rank_str} | {r['recall_at_k']:.3f} | {r['reciprocal_rank']:.3f} |"
        )

    if result["n_negative"]:
        lines += [
            "",
            "## Negative queries (no relevant doc in corpus)",
            "",
            "Top-1 score is the system's *confidence* on an unanswerable query — "
            "lower is better (less false confidence). The grounded prompt in "
            "`generate.ask` is what turns this signal into the fixed IDK sentence.",
            "",
            "| Query | Top-1 doc_id | Top-1 score |",
            "|---|---|---|",
        ]
        for r in result["rows"]:
            if not r["is_negative"]:
                continue
            top = r["top_hits"][0] if r["top_hits"] else None
            top_id = f"`{top['doc_id']}`" if top else "—"
            top_score = f"{r['top1_score']:.3f}" if r["top1_score"] is not None else "—"
            lines.append(f"| {r['query']} | {top_id} | {top_score} |")

    lines += ["", "## Top hits per query", ""]
    for r in result["rows"]:
        lines.append(f"### {r['query']}")
        lines.append("")
        relevant_str = ", ".join(r["relevant"]) if r["relevant"] else "(none — negative query)"
        lines.append(f"Relevant: `{relevant_str}`")
        lines.append("")
        lines.append("| Rank | Score | doc_id | Title |")
        lines.append("|---|---|---|---|")
        for i, h in enumerate(r["top_hits"], 1):
            marker = " (*)" if h["doc_id"] in r["relevant"] else ""
            lines.append(f"| {i} | {h['score']:.3f} | `{h['doc_id']}`{marker} | {h['title']} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=settings.top_k)
    parser.add_argument("--out", type=Path, default=None, help="Optional markdown output path.")
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
