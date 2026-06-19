"""Section 4: FastAPI surface.

Thin transport layer. All real work lives in :mod:`lac_ai.retrieve` and
:mod:`lac_ai.generate`; this file only validates I/O and translates exceptions
to HTTP errors. The CLI calls the same core functions, so HTTP and CLI never
diverge.

Run with: ``uvicorn lac_ai.api:app --reload``
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from lac_ai import __version__
from lac_ai.config import settings
from lac_ai.generate import ask as ask_core
from lac_ai.retrieve import search as search_core

app = FastAPI(title="Lac_ai", version=__version__)


class HealthResponse(BaseModel):
    status: str
    version: str
    embedding_model: str
    llm_model: str
    collection: str


class HitOut(BaseModel):
    doc_id: str
    title: str
    text: str
    url: str
    score: float


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int | None = Field(default=None, ge=1, le=50)


class SearchResponse(BaseModel):
    query: str
    hits: list[HitOut]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    k: int | None = Field(default=None, ge=1, le=50)


class AskResponse(BaseModel):
    question: str
    text: str
    citations: list[str]
    retrieved: list[HitOut]
    model: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        embedding_model=settings.embedding_model,
        llm_model=settings.llm_model,
        collection=settings.collection,
    )


@app.post("/search", response_model=SearchResponse)
def post_search(req: SearchRequest) -> SearchResponse:
    hits = search_core(req.query, k=req.k)
    return SearchResponse(
        query=req.query,
        hits=[HitOut(**h.to_dict()) for h in hits],
    )


@app.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    try:
        ans = ask_core(req.question, k=req.k)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AskResponse(
        question=ans.question,
        text=ans.text,
        citations=ans.citations,
        retrieved=[HitOut(**h.to_dict()) for h in ans.retrieved],
        model=ans.model,
    )
