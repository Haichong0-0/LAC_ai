from __future__ import annotations

from lac_ai.retrieve import Hit, search


def test_search_returns_hits_in_expected_shape(seeded_collection, fake_embedder):
    hits = search("apple red sweet", k=3, embedder=fake_embedder)
    assert hits
    assert all(isinstance(h, Hit) for h in hits)
    top = hits[0]
    # toy embedder hashes last letter; "apple" should match "apple" doc
    assert top.doc_id == "apple"
    assert top.title == "Apple"
    assert 0.0 <= top.score <= 1.0


def test_search_respects_k(seeded_collection, fake_embedder):
    hits = search("anything", k=2, embedder=fake_embedder)
    assert len(hits) == 2


def test_search_empty_query_returns_empty(seeded_collection, fake_embedder):
    assert search("   ", k=5, embedder=fake_embedder) == []
