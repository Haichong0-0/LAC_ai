"""Typer CLI. Subcommands are added as each section lands."""

from __future__ import annotations

import typer

from lac_ai import ingest as ingest_mod

app = typer.Typer(add_completion=False, help="Lac_ai — small RAG over Wikipedia.")


@app.command()
def ingest() -> None:
    """Section 1: fetch Wikipedia summaries into data/corpus.jsonl."""
    stats = ingest_mod.ingest()
    typer.echo(
        f"ingest: total={stats['total']} fetched={stats['fetched']} "
        f"skipped={stats['skipped']} missing={stats['missing']}"
    )


if __name__ == "__main__":
    app()
