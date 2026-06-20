from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lac_ai import api as api_mod
from lac_ai.generate import Answer
from lac_ai.retrieve import Hit


@pytest.fixture
def client(seeded_collection, fake_embedder, monkeypatch):
    # Skip the lifespan model preload — we have a fake embedder via conftest.
    monkeypatch.setattr(api_mod, "get_default_embedder", lambda: fake_embedder)
    with TestClient(api_mod.app) as c:
        yield c


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "embedding_model" in body


def test_search_returns_hits(client):
    r = client.post("/search", json={"query": "apple red sweet", "k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "apple red sweet"
    assert len(body["hits"]) == 2
    assert body["hits"][0]["doc_id"] == "apple"


def test_search_rejects_empty_query(client):
    r = client.post("/search", json={"query": "", "k": 2})
    assert r.status_code == 422


def test_ask_returns_503_without_api_key(client, monkeypatch):
    from lac_ai.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", None)
    # Bypass the IDK threshold so this query reaches the API-key check.
    monkeypatch.setattr(settings, "min_score", 0.0)
    r = client.post("/ask", json={"question": "apple red sweet"})
    assert r.status_code == 503
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_ask_uses_injected_core(client, monkeypatch):
    fake_answer = Answer(
        question="apple?",
        text="Apples are a fruit [apple].",
        citations=["apple"],
        retrieved=[Hit(doc_id="apple", title="Apple", text="x", url="http://x", score=0.9)],
        model="fake-model",
    )
    monkeypatch.setattr(api_mod, "ask_core", lambda *a, **kw: fake_answer)
    r = client.post("/ask", json={"question": "apple?", "k": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "Apples are a fruit [apple]."
    assert body["citations"] == ["apple"]
    assert body["model"] == "fake-model"
    assert body["retrieved"][0]["doc_id"] == "apple"
