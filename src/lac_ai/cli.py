"""Typer CLI. Subcommands are added as each section lands."""

from __future__ import annotations

import typer

from lac_ai import embed as embed_mod
from lac_ai import generate as generate_mod
from lac_ai import ingest as ingest_mod
from lac_ai import retrieve as retrieve_mod

app = typer.Typer(add_completion=False, help="Lac_ai — small RAG over Wikipedia.")


@app.command()
def ingest() -> None:
    """Section 1: fetch Wikipedia summaries into data/corpus.jsonl."""
    stats = ingest_mod.ingest()
    typer.echo(
        f"ingest: total={stats['total']} fetched={stats['fetched']} "
        f"skipped={stats['skipped']} missing={stats['missing']}"
    )


@app.command()
def embed() -> None:
    """Section 2: normalize → chunk → embed → upsert into Chroma."""
    stats = embed_mod.build_index()
    typer.echo(f"embed: processed={stats['processed']} upserted={stats['upserted']} skipped={stats['skipped']}")


@app.command()
def search(query: str, k: int = typer.Option(None, "--k", help="Top-K override.")) -> None:
    """Section 3: top-K retrieval (no LLM call)."""
    hits = retrieve_mod.search(query, k=k)
    if not hits:
        typer.echo("(no hits)")
        return
    for i, h in enumerate(hits, 1):
        typer.echo(f"{i:>2}. {h.score:.3f}  {h.title}  ({h.doc_id})")


@app.command()
def ask(question: str, k: int = typer.Option(None, "--k", help="Top-K override.")) -> None:
    """Section 3: full RAG — retrieve and ask Claude."""
    ans = generate_mod.ask(question, k=k)
    typer.echo(ans.text)
    if ans.citations:
        typer.echo("")
        typer.echo("Citations:")
        for c in ans.citations:
            typer.echo(f"  - {c}")


if __name__ == "__main__":
    app()
