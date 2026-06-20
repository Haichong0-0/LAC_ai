from __future__ import annotations

from lac_ai.embed import normalize


def test_normalize_strips_citation_markers():
    assert normalize("foo[1] bar[23]") == "foo bar"


def test_normalize_collapses_whitespace():
    assert normalize("hello    world\tfoo") == "hello world foo"


def test_normalize_nfc_unicode():
    # decomposed form: e + combining acute
    decomposed = "café"
    composed = "café"
    assert normalize(decomposed) == composed


def test_normalize_strips_trailing_whitespace():
    assert normalize("  hello world  ") == "hello world"
