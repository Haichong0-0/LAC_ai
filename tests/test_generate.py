from __future__ import annotations

from lac_ai.generate import IDK_SENTENCE, _extract_citations, ask
from lac_ai.retrieve import Hit


def _hit(doc_id: str) -> Hit:
    return Hit(doc_id=doc_id, title=doc_id, text="x", url="http://x", score=0.9)


def test_extract_citations_keeps_only_real_doc_ids():
    hits = [_hit("apple"), _hit("banana")]
    text = "Apples are red [apple] and also [fictional_doc] and [banana] again [apple]."
    cites = _extract_citations(text, hits)
    # hallucinated id dropped; real ids deduped in order of first appearance
    assert cites == ["apple", "banana"]


def test_extract_citations_empty_when_no_brackets():
    assert _extract_citations("plain answer with no citations", [_hit("apple")]) == []


def test_ask_short_circuits_to_idk_when_no_hits(seeded_collection, fake_anthropic):
    # query the toy collection with something that still yields hits — so force empty by k=0?
    # Instead, monkey out search to return [] for this one call.
    from lac_ai import generate as generate_mod

    original = generate_mod.search
    generate_mod.search = lambda *a, **kw: []
    try:
        ans = ask("anything", client=fake_anthropic)
    finally:
        generate_mod.search = original

    assert ans.text == IDK_SENTENCE
    assert ans.citations == []
    assert ans.retrieved == []
    # Crucially, no call was made to Claude.
    assert fake_anthropic.calls == []


def test_ask_calls_claude_when_hits_present(seeded_collection, fake_anthropic):
    fake_anthropic.set_reply("Apples are a fruit [apple].")
    # min_score=0.0 bypasses the threshold so the toy FakeEmbedder's scores
    # don't accidentally trip the IDK short-circuit.
    ans = ask("apple red sweet", client=fake_anthropic, k=2, min_score=0.0)
    assert ans.text == "Apples are a fruit [apple]."
    assert "apple" in ans.citations
    assert ans.retrieved  # non-empty
    assert len(fake_anthropic.calls) == 1
    # System prompt is set and forbids outside knowledge.
    sys_prompt = fake_anthropic.calls[0]["system"]
    assert "Only use facts that appear in the context" in sys_prompt
    assert IDK_SENTENCE in sys_prompt


def test_ask_short_circuits_to_idk_when_top_score_below_threshold(seeded_collection, fake_anthropic):
    """A borderline retrieval (top hit exists but score is low) must skip Claude."""
    # min_score is set absurdly high — guarantees the top-1 toy score is below it.
    ans = ask("apple red sweet", client=fake_anthropic, k=2, min_score=0.999999)
    assert ans.text == IDK_SENTENCE
    assert ans.citations == []
    # Hits are still returned so the caller can inspect what was considered.
    assert ans.retrieved, "should still surface what was considered for debuggability"
    # Crucially, Claude was never called — that's the whole point of the threshold.
    assert fake_anthropic.calls == []
