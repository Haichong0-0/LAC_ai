"""Section 3b: grounded QA over the retrieved context using Claude.

The prompt forces three properties that make the eval honest:

1. Answers must be drawn only from the provided context (no outside knowledge).
2. Each claim must carry an inline ``[doc_id]`` citation matching a retrieved hit.
3. If the context does not support an answer, the model must reply with a fixed
   "I don't know" sentence.

"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from anthropic import Anthropic

from lac_ai.config import settings
from lac_ai.retrieve import Hit, search

IDK_SENTENCE = "I don't know based on the provided context."

SYSTEM_PROMPT = f"""You answer questions strictly from the context block provided by the user. Each \
context item is introduced on its own line as `[doc_id] Title` and followed by the article text.

Rules:
1. Only use facts that appear in the context. Do not use outside knowledge.
2. After each factual claim, cite the doc_id(s) that support it inline in square brackets, e.g. \
"C was created by Dennis Ritchie [c_(programming_language)]". Use the exact doc_id strings from the context.
3. If the context does not contain enough information to answer the question, reply with exactly \
this sentence and nothing else: "{IDK_SENTENCE}"
4. Keep answers concise — one or two short paragraphs at most."""

_CITATION_RE = re.compile(r"\[([a-z0-9_().+\-]+)\]")


@dataclass(frozen=True)
class Answer:
    question: str
    text: str
    citations: list[str] = field(default_factory=list)
    retrieved: list[Hit] = field(default_factory=list)
    model: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["retrieved"] = [h.to_dict() if isinstance(h, Hit) else h for h in self.retrieved]
        return d


def _format_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{h.doc_id}] {h.title}\n{h.text}" for h in hits)


def _extract_citations(answer_text: str, retrieved: list[Hit]) -> list[str]:
    valid = {h.doc_id for h in retrieved}
    seen: list[str] = []
    for m in _CITATION_RE.findall(answer_text):
        if m in valid and m not in seen:
            seen.append(m)
    return seen


def ask(
    question: str,
    k: int | None = None,
    model: str | None = None,
    client: Anthropic | None = None,
    min_score: float | None = None,
) -> Answer:
    """Retrieve top-K context and ask Claude. Returns an :class:`Answer`.

    If the top-1 retrieval score is below ``min_score`` (or no hits at all),
    short-circuits to the fixed IDK sentence without calling Claude. The
    retrieved hits are still returned for debuggability so callers can see
    what the system *considered* before refusing.
    """
    k = k or settings.top_k
    model = model or settings.llm_model
    min_score = settings.min_score if min_score is None else min_score
    hits = search(question, k=k)

    if not hits or hits[0].score < min_score:
        return Answer(
            question=question,
            text=IDK_SENTENCE,
            citations=[],
            retrieved=hits,
            model=model,
        )

    if client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set — copy .env.example to .env and fill it in.")
        client = Anthropic(api_key=settings.anthropic_api_key)

    user_message = f"Context:\n\n{_format_context(hits)}\n\nQuestion: {question}"
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    answer_text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()

    return Answer(
        question=question,
        text=answer_text,
        citations=_extract_citations(answer_text, hits),
        retrieved=hits,
        model=model,
    )
