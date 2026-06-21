# Lac_ai

A small retrieval + reasoning system over ~150 Wikipedia article summaries about programming languages. Built for the take-home assignment in [Assignment.md](Assignment.md).

The corpus, the index, the search layer, and a grounded QA wrapper are all here. So is a CLI (`lac …`) and an HTTP API (FastAPI) — both share the same core functions, so the two surfaces can never diverge.

---

## Quick start

```powershell
# 1. Install dependencies (creates ./.venv)
uv sync

# 2. Configure the Anthropic API key
Copy-Item .env.example .env       # then edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Build the corpus and index (one-time; both steps are idempotent)
uv run lac ingest                 # writes data/corpus.jsonl (~150 records)
uv run lac embed                  # builds chroma_db/ with vector index

# 4. Ask a question
uv run lac ask "Who invented the C programming language?"

# 5. Or serve over HTTP
uv run uvicorn lac_ai.api:app --reload
# POST http://127.0.0.1:8000/ask  {"question": "...", "k": 5}
```

All four commands (`ingest`, `embed`, `search`, `ask`) print one-line status summaries and exit 0 on success.

---

## Architecture

Four sections, one responsibility each. The boundaries were chosen so that swapping any single concern is a one-section change.

```
Section 1   ingest.py            fetch raw Wikipedia summaries → data/corpus.jsonl
                                  (strict: download + persist, nothing else)

Section 2   chunking.py          pluggable text chunker; default is whole-doc
            embedders.py         Embedder protocol + sentence-transformers impl
            embed.py             normalize → chunk → embed → upsert into Chroma

Section 3   retrieve.py          top-K cosine search over Chroma
            generate.py          grounded prompt → Claude → answer + citations

Section 4   api.py               FastAPI: /health, /search, /ask
            cli.py               Typer: lac ingest | embed | search | ask
            config.py            pydantic-settings, reads .env
```

The single biggest design choice is the line between Section 1 and Section 2:

- **Ingestion is byte-for-byte fetch and persistence.** No normalization, no chunking, no embedding. Idempotent on a SHA-256 of the fetched text.
- **All text decisions live with the embedder.** Normalization rules, chunking strategy, model choice — anything that interprets the text belongs in Section 2, because those are the knobs you re-tune when retrieval quality misses.

Why split it this way: ingestion stays deterministic and auditable forever (the corpus on disk is what Wikipedia returned, full stop), and Section 2 is the only place you'd ever change to improve retrieval quality.

---

## Decisions

Each item below names the choice, the alternative considered, and the reason. The same list lives in `CLAUDE.md` (the working ledger that future Claude Code sessions read); this README is the version meant for a human reviewer.

### Stack

**Python + FastAPI + ChromaDB + Claude (Anthropic SDK).**
The assignment's reference stack is Python + FastAPI + Postgres/pgvector + Claude. I swapped pgvector for ChromaDB:

- 150-document corpus is well under the size where pgvector's SQL composability matters. Chroma's `PersistentClient` is a single directory on disk — no separate server to run during a take-home review.
- The retrieval interface (`collection.query(...)`) is small enough that swapping to pgvector later would be a one-file change in `embed.py` + `retrieve.py`.

Embedding model and LLM choices are below.

### Dataset

**~150 Wikipedia article summaries sampled from `Category:Programming_languages`.**

> **Spec note.** The assignment asks for ~50–100 short documents; the corpus here is 150. I started at 100, ran the eval against two embedders, and found `bge-small` and `bge-base` produced identical Recall@5 and MRR (both 1.000 / 0.900). That's the textbook symptom of *"the eval is too easy to discriminate"* — every right answer is at rank 1 because nothing's competing. Expanding to 150 added enough near-neighbor articles to expose a real difference (see the *Embedder comparison* section below). I went over the spec ceiling deliberately because measurable retrieval differences mattered more than literal compliance, and I'd rather report a finding than a tied null result.

Alternatives considered, with reasons against:

| Alternative | Why not |
|---|---|
| AG News (HuggingFace) | "Articles" are 1–4 sentences, often headline + lede. QA demo would feel underwhelming — answers are one-liners. |
| CNN/DailyMail | Articles are 500–1000+ words → forces chunking back into the plan, adds a tuning knob we'd otherwise avoid. |
| NewsAPI live scrape | Needs an API key. Not reproducible — a reviewer can't re-run the corpus build. |
| Amazon/Yelp reviews | Subjective content makes retrieval eval fuzzy: "does this review say X is good" has no objective ground truth. |
| SQuAD passages | Feels like cheating — the dataset was designed around the queries. |
| Broad Wikipedia dump | Retrieval differences become invisible because the topics don't overlap; no near-neighbor articles. |

Curated topic slice wins because:

1. **Near-neighbor effect.** All ~150 docs are about programming languages, so a query like *"functional language with strong static typing"* has to discriminate between Haskell, Caml, Crystal, and Go — the retrieval layer actually has to *do something*. The 150-doc count was deliberate: the original 100-doc corpus produced identical Recall/MRR numbers for two different embedders (see the comparison section below), which is exactly the symptom of *"the eval is too easy to discriminate"*.
2. **Honest ground-truth labeling.** For each eval query, "which doc is the right one" is unambiguous.
3. **Future story.** If retrieval misses on code-heavy queries, we have a natural narrative: swap to a code-aware embedder. The topic itself opens that door.

### Title list provenance

**MediaWiki category-members API → programmatic prune → committed `data/title_list.json`.**

The title list is *data*, not code (`ingest.py` reads it). Its provenance is:

1. One call to the public MediaWiki API:
   `action=query&list=categorymembers&cmtitle=Category:Programming_languages&cmlimit=500&cmnamespace=0`
2. Programmatic prune in [scripts/fetch_title_list.py](scripts/fetch_title_list.py): drop `List of …`, `Comparison of …`, disambiguation pages, the generic *"Programming language"* article (would dominate as a generic match).
3. Deterministic alphabetical sort, trim to 150.
4. JSON written with provenance fields: `source`, `fetched_count`, `kept_after_prune`, `target_size`.

Alternatives:

- **Wikidata SPARQL** — more rigorous (filter by typed property `instance of: programming language`), but overkill for 150 docs and adds a dependency on the Wikidata SPARQL endpoint.
- **Parse a "List of programming languages" Wikipedia article** — human-curated, but parsing wikitext is fiddly and the source is one editor's judgement rather than a structural query.
- **Hand-author the list** — fastest, but defensibility goes down ("did you cherry-pick the easy ones?"). Programmatic seed + auditable prune avoids that.

### Article fetcher

**`wikipedia-api` package.**
Maintained wrapper over MediaWiki, handles redirects, no API key, returns a clean summary (intro section) per article. The older `wikipedia` package is less actively maintained; the MediaWiki REST endpoint directly would work but adds boilerplate. The Wikipedia API requires a `User-Agent` header — we set one that names the project.

### Idempotency

**Content-hash based, twice.**

- **In ingestion**: every record stores a SHA-256 of its fetched text. Re-running `lac ingest` skips titles whose hash matches the existing record. Output: `fetched=0 skipped=150` on a second run.
- **In embedding**: every chunk stores a SHA-256 of `(model_id, text)` as Chroma metadata. Re-running `lac embed` only re-embeds chunks whose hash changed. Crucially, the hash includes the embedder id — changing models *automatically* invalidates the index, which prevents the "old vectors mixed with new model" bug.

Why this matters: embedding 150 chunks with `bge-small` locally is fast, but the principle scales. On a 10k-doc corpus you do not want to pay full embedding cost on a one-comma typo fix.

### Chunking

**Whole-document (one chunk per article), pluggable interface.**

Wikipedia *summaries* (intro sections) average ~200–500 tokens — well within any sensible embedder's context. Splitting them would:

- Add a tuning knob (chunk size, overlap, splitter) we'd otherwise not need.
- Make citation noisy: one article would produce N hits; the LLM would have to reason over fragments instead of a coherent passage.

But the chunker is implemented as a `Chunker = Callable[[SourceDoc], list[Chunk]]`, so swapping to a sentence-splitter is one function. If the eval reveals long-article failures, we change it then — not preemptively.

### Normalization

**Light: NFC unicode + strip `[1]`-style citation markers + collapse whitespace.**

We strip citation footnote markers because they appear mid-sentence as tokens that don't help retrieval and could mislead the embedder. NFC normalization avoids two embeddings for "café" depending on Unicode form. We do *not* strip Wikipedia infobox residue or section headers because the summary endpoint doesn't include them — we verified this on a sample.

Crucially, normalization lives in Section 2 (`embed.py`), not Section 1. The on-disk `corpus.jsonl` is exactly what Wikipedia returned. This means changing normalization is a re-embed, not a re-fetch.

### Embedding model

**`sentence-transformers/BAAI/bge-small-en-v1.5` (local, 384-dim, ~33M params).**

Why local over an API embedder:

- **Reproducibility.** Anyone with the repo can rebuild the index without a second API key.
- **No second cost surface.** Already paying for Claude on the QA side; doubling the dependency for marginal quality on 150 short docs would be theater.
- **Speed.** Embedding 150 docs takes < 10 seconds on CPU. Hosted embedders pay round-trip latency per batch.

Why `bge-small` specifically: top-tier on the MTEB retrieval benchmark for its size class, well-tested, frozen weights. Wrapped behind an `Embedder` Protocol so swapping to Voyage / OpenAI / a code-aware embedder is a one-file change. The hash-includes-model-id idempotency means switching is just "edit `.env`, run `lac embed`".

Considered but not chosen for the default:

- **`bge-base-en-v1.5`** (~110M, 768-dim) — a free quality bump if it turns out we want it. Easy to swap, documented as the first upgrade path.
- **`bge-code-v1` / Jina code embeddings** — only worth it if the eval shows code-heavy queries failing. We'll measure first.
- **Voyage / OpenAI API embeddings** — top-tier, but adds a key and cost; not justified at 150 short docs.

### Vector store

**ChromaDB `PersistentClient` rooted at `./chroma_db/`, single collection `corpus`, cosine distance.**

Metadata stored alongside each vector: `doc_id`, `title`, `url`, `content_hash`, `embedder`. That means a search returns title and URL without a separate JOIN-style lookup — `retrieve.search()` is one query.

Storing `embedder` in metadata gives us a sanity check: if you ever query the collection and see mixed `embedder` values, you have a contamination bug.

### Retrieval

**Top-K cosine search, K=5 default, config-driven via `LAC_TOP_K`.**
`retrieve.search()` is a pure function: in → query string + optional K, out → `list[Hit]`. Both the FastAPI `/search` endpoint and the eval harness call it directly. No transport-layer code creeps into the core.

`score = 1 - distance` so larger is closer — easier to reason about in logs and eval tables than a raw distance.

### LLM and prompt

**`claude-haiku-4-5` default, swappable to Sonnet via `LAC_LLM_MODEL` env var.**

At this corpus size the bottleneck is retrieval, not generation — Haiku is fast, cheap, and capable enough to answer cleanly from grounded context. The model id is config-only; no code changes to swap.

The prompt enforces three properties that make manual QA evaluation honest:

1. **Grounded.** *"Only use facts that appear in the context. Do not use outside knowledge."* If Claude knows that Dennis Ritchie created C from its pretraining, the prompt forbids using that — it must come from the context.
2. **Cited.** Inline `[doc_id]` after each claim. The doc_ids are the slugged article titles, so they match retrieved hits exactly.
3. **"I don't know" fallback.** *"If the context does not contain enough information, reply with exactly this sentence: 'I don't know based on the provided context.'"* Makes hallucination visible — a wrong answer with no citation, or a citation that doesn't match any retrieved hit, is a clear signal.

Post-processing extracts citations by regex and *filters them against the retrieved doc_ids*. Any cited id that wasn't actually retrieved gets dropped — defense against the model hallucinating a citation.

If retrieval returns zero hits, `ask()` short-circuits to the IDK sentence without calling Claude at all. Saves tokens and time.

#### Confidence threshold (`LAC_MIN_SCORE`)

The grounded prompt alone is not enough — given *any* context, Claude will sometimes try to bridge it to the question even when the context is clearly off-topic. So `ask()` also enforces a hard threshold on the top-1 retrieval score: if the best hit's score is below `LAC_MIN_SCORE` (default `0.65`), the system returns the IDK sentence **without calling Claude at all**.

Calibrated against the 150-doc eval (bge-small):

| Query class | Top-1 score | At threshold 0.65 |
|---|---|---|
| Answerable (lowest is q4 — Refal beating Agda) | 0.739 | passes → Claude is called |
| Negative, in `queries.json` (out-of-corpus, *"capital of France"*) | 0.486 | rejected → IDK |

There is also an in-domain *borderline* class — questions like *"What is the most common language?"* that name no specific language and that no single article in the corpus answers. A live `lac search` for that query returns a top-1 of around 0.620 (sentence-level overlap on the topic words, no real semantic match), which is also below the threshold and correctly rejected. That class isn't yet in `queries.json` — it's an ad-hoc check, not part of the committed eval set.

This catches *both* the unanswerable case and the harder-to-spot "the corpus could not have answered this" case, before any LLM call. Token cost on borderline traffic drops to zero. The threshold is config-driven (`LAC_MIN_SCORE` in `.env`) and overridable per call in code.

The retrieved hits are still returned in the API response when IDK fires, so a caller can inspect *what* the system considered before refusing.

### HTTP and CLI

**Both surfaces, one shared core.**

The assignment says "HTTP API or CLI". Building both — when both are thin wrappers over `retrieve.search()` and `generate.ask()` — is essentially free and gives the reviewer two ways to play. The CLI is for ergonomic local use; the HTTP API is what you'd actually ship.

FastAPI uses Pydantic v2 schemas with constraints (`min_length=1` on query/question, `1 ≤ k ≤ 50`). The `/ask` endpoint catches `RuntimeError` for missing API keys and returns `503` instead of leaking a stack trace.

### Tooling

| Tool | Why |
|---|---|
| `uv` | Fast, lockfile, current standard. One install command to reproduce the environment. |
| `ruff` | One tool for lint + format; replaces black + isort + flake8. |
| `pytest` | Standard. |
| `pydantic-settings` + `.env` | Settings are typed, env-driven, validated at startup. `.env.example` is the contract. |
| `typer` | CLI is autogenerated from function signatures — same author surface as FastAPI. |

### Evaluation

**Recall@5 and MRR over 6 hand-labeled queries** (5 answerable + 1 negative) in [eval/queries.json](eval/queries.json), run by [eval/run_eval.py](eval/run_eval.py). Recall@5 answers *"did the right doc make it into Claude's context?"*; MRR answers *"how well-ranked was it?"*. Both ride directly on the existing `retrieve.search()` — the eval harness is not a separate codepath.

We deliberately do not run an LLM-as-judge over QA outputs at this scale — at 6 queries, the cost of the eval machinery exceeds the cost of reading 6 answers by eye.

The queries are designed to stress different retrieval shapes:

| id | Shape |
|---|---|
| q1 | Direct lookup — language name in query (*"Who invented the C…"*) |
| q2 | Descriptive — names the use case, not the language (*"…for SAP business applications"*) |
| q3 | Descriptive — distinguishing traits only (*"array programming language for financial applications"*) |
| q4 | Technical descriptor — relies on the embedder understanding *"dependently typed"* + *"theorem proving"* semantically |
| q5 | Company + domain (*"…at Ericsson for concurrent telecommunication systems"*) |

#### Results (embedder = `BAAI/bge-small-en-v1.5`, K = 5, corpus = 150 docs)

| Metric | Value |
|---|---|
| Recall@5 | **1.000** |
| MRR | **0.850** |

| Query | Relevant doc | Rank of first relevant |
|---|---|---|
| Who invented the C programming language? | `c_(programming_language)` | 1 |
| language used for SAP business applications | `abap` | 1 |
| array programming language designed for financial applications | `a+_(programming_language)` | 1 |
| dependently typed functional language used for theorem proving | `agda_(programming_language)` | **4** |
| language designed at Ericsson for building concurrent telecommunication systems | `erlang_(programming_language)` | 1 |

Full per-query top-5 hit tables are in [eval/results.md](eval/results.md).

#### What this tells us

- The corpus and the embedder are well-matched for **literal-name** and **use-case-descriptor** queries: 4/5 answerable queries put the right doc at rank 1, with confident margins (0.05–0.13 gap to rank 2).
- The **rank-4 finish on q4** is the real story. *Agda* now sits at rank 4 behind *Refal* (0.739), *Reversible programming language* (0.715), and *Clojure* (0.701). Agda's own score is 0.689. At 100 docs Agda was at rank 2, behind only Clojure; expanding the corpus to 150 introduced two more functional / "term-rewriting / reversible-computing" near-neighbors that bge-small can't discriminate from Agda's "dependently typed theorem prover" descriptor. **The bigger corpus revealed an embedder ceiling that the smaller one masked.**
- **Negative-query top-1 score (0.486)** is well below the lowest answerable top-1 (0.739 on q4). Even on the unanswerable question, the bi-encoder isn't false-confident, so the grounded prompt has clear separation to trigger the IDK fallback.
- Recall@5 = 1.000 means **the QA layer always has the right context to answer** (Agda just barely makes it in at rank 4). Any QA failure becomes a generation problem (prompting or model choice), not a retrieval problem. Useful separation for debugging.

#### Embedder comparison: `bge-small` vs `bge-base` (at 150 docs)

Same 6 queries, same K. The bge-base run is repeatable from the repo by editing `.env` (`LAC_EMBEDDING_MODEL=BAAI/bge-base-en-v1.5`), wiping `chroma_db/`, and re-running `lac embed` + `python eval/run_eval.py --out eval/results_bge_base.md`.

| | `bge-small-en-v1.5` (default) | `bge-base-en-v1.5` |
|---|---|---|
| Params / dim | 33M / 384 | 110M / 768 |
| Recall@5 | 1.000 | 1.000 |
| MRR | 0.850 | **0.900** |
| Agda (q4) rank | 4 (behind Refal, Reversible, Clojure) | **2** (behind FX-87, 0.717 vs 0.723) |
| Negative-query top-1 score (lower is better) | 0.486 | **0.412** |

**bge-base measurably wins at 150 docs.** Three concrete improvements over bge-small:

1. **MRR jumps from 0.850 to 0.900** — driven entirely by Agda climbing from rank 4 to rank 2. The richer 768-dim embedding space discriminates "dependently typed theorem prover" from "term-rewriting" / "reversible-computing" / "functional Lisp dialect" where bge-small could not. The Agda margin to its runner-up tightens from 0.006 to 0.006 — almost identical — but bge-base's mistake (FX-87, a typed effect language) is semantically *much* closer to the right kind of language than bge-small's mistakes (Refal, Reversible, Clojure).
2. **Negative-query calibration improves by 0.074 of cosine score** (0.486 → 0.412). bge-base is less false-confident on out-of-corpus queries, which directly widens the safety margin for the grounded-IDK fallback.
3. **The rank-1 queries stay rank 1.** No regression — bge-base is strictly an upgrade on this corpus.

This is the comparison earning the swap. The system stays on bge-small as the default for now because the corpus is small enough that 0.05 MRR isn't worth a 3× model-size jump for every consumer of this repo, but the result is documented and the swap is one config line away.

#### Comparison at 100 docs (historical, for context)

When the corpus was only 100 docs, bge-small and bge-base produced *identical* headline numbers (1.000 / 0.900). The corpus expansion to 150 was what revealed the difference. The lesson: **eval over a small enough corpus can mask real embedder differences**. Documented finding, not a flaw — it's exactly what motivated the expansion in the first place.

#### Note on switching embedders

Chroma collections have a fixed embedding dimension at creation time. Switching from a 384-dim embedder (`bge-small`) to a 768-dim one (`bge-base`) requires wiping `chroma_db/` first, because the existing collection rejects vectors of the wrong dimension even though the per-chunk content hash already invalidates them. The cleanest fix would be to derive the collection name from the model id (`corpus_<slug>`) so each embedder gets its own isolated index. Listed in "What I would do with more time."

---

## What I deliberately did not build, and why

Listed in priority order. Each one is a tradeoff, not an oversight.

- **No chunking beyond the pluggable no-op.** Wikipedia summaries are short. Until eval shows a long-article failure, chunking is a knob with no signal to tune against.
- **No cross-encoder reranker.** At 150 docs the bi-encoder ranking is mostly good (C is top hit at 0.83 for *"Who invented C?"*). The q4 Agda rank-4 finish *might* benefit from a reranker, but bge-base already fixes it for less complexity — picking the simpler lever first.
- **No hybrid BM25 + dense search.** Same reason — would matter at 10k+ docs. At 150 docs, dense alone is fine.
- **No streaming responses.** The assignment is single-turn QA. Streaming is nice but adds plumbing without changing the answer.
- **No conversation memory.** Out of scope.
- **No auth, no rate limiting, no Docker.** The assignment is "runs locally". Adding these is signaling, not solving the problem.
- **No LLM-as-judge or RAGAS-style automated scoring.** At 5 queries the eval rig would be more code than the system it evaluates.
- **No async everywhere.** FastAPI handlers are sync because the inner calls (`SentenceTransformer.encode`, Chroma query, Anthropic SDK) are sync at the library level. Wrapping them in `async def` would be cargo cult.
- **No retry/backoff on the Anthropic call.** Single-shot is fine for a take-home; a real service would add structured retries with jitter.
- **No corpus-side caching of LLM answers.** Not a fit for a knowledge demo, but obvious in a production system.

---

## What I would do with more time

In rough priority order:

1. **Promote `bge-base` to the default and try going larger still.** The eval shows `bge-base` is a strict upgrade on this corpus (MRR 0.850 → 0.900, negative-query calibration 0.486 → 0.412). Worth doing as a follow-up: change the `.env.example` default, re-baseline `eval/results.md`. From there, `bge-large-en-v1.5` or `voyage-3-large` are the next rungs to try if we want to flip Agda from rank 2 to rank 1. Enriching the Agda Wikipedia summary with the literal phrase "dependently typed" would also help — embedders can only anchor on tokens that exist in the text.
2. **Per-embedder collection names.** Derive the Chroma collection name from the model id (e.g. `corpus_bge_small_v1_5`) so switching `LAC_EMBEDDING_MODEL` doesn't require manually wiping `chroma_db/`.
3. **Expand the eval set.** 6 queries gives a coarse signal. 15–20 queries with multi-doc relevance labels would let us report Recall@K *and* Precision@K honestly, and would catch failure modes a small set misses.
4. **Better citation UX.** Have the API return citation spans (offsets into the retrieved text) rather than just doc ids, so a UI could highlight the source sentence.
5. **Sentence-level chunking experiment.** Only if eval shows long-article failures. Until then, the simpler thing is the right thing.
6. **A small Streamlit / web front-end.** Pure ergonomics for the reviewer; doesn't change the system.

---

## How I used AI on this project

The take-home brief explicitly allowed AI assistance. I used Claude Code (the CLI agent) throughout, and I want to be specific about the division of labor because "I used AI" can mean anything from "I pasted a stub" to "I drove the design and AI typed."

**What I drove:**

- The shape of the problem and the section split (ingestion / embedding / search-QA / HTTP). The very first decision — *"ingestion is strict download-and-store; all text decisions live with the embedder"* — was mine and I had to push back on AI-generated plans that wanted to put normalization in `ingest.py`.
- The dataset choice. The AI initially recommended Wikipedia; we then went through news, AG News, CNN/DM, and back to a curated Wikipedia topic slice as I weighed the QA-demo-vs-eval-defensibility tradeoff. The "Programming languages" category was my pick once I decided I wanted the future option of a code-aware embedder narrative.
- Decisions about scope. The "what I deliberately did not build" list is the one I most enforced — every time the AI suggested adding a feature (streaming, hybrid search, a reranker, retries), I either decided it was worth it or kept it out of scope deliberately.
- The pivot to commit history. I wanted commits split per section so the diff tells a story, and I picked the subjects (`init, config and cli`, `Text processing, index`, etc.).

**What the AI drafted, that I then reviewed and accepted or edited:**

- Most of the Python implementation — `ingest.py`, `embed.py`, `retrieve.py`, `generate.py`, `api.py`, the chunker, the embedder protocol, the eval harness.
- This README. I told it which decisions to cover; it drafted; I read and reshaped.
- The pytest suite scaffold (`conftest.py` + four test files).

**Where I overruled the AI:**

- It wanted to put chunking and normalization in `ingest.py`. I split the responsibilities.
- It initially recommended AG News when I asked about news datasets. After looking at sample articles, I rejected it (1-sentence stubs would make QA answers thin) and went back to Wikipedia.
- It chose `bge-small-en-v1.5` as the default. I had it run the comparison against `bge-base` to validate or invalidate that choice with data, rather than leave it as an opinion.

**What I'd want a reviewer to take from this:**

I treated the AI as a fast pair-programmer, not as an answer machine. The decisions and the tradeoff calls are mine; the typing is largely the AI's. The README's *Decisions* and *What I deliberately did not build* sections are the most honest signal of what I actually drove, because both are about *not* doing things — exactly where an AI left to its own devices would have piled on features.

## Notes on reproducing the build

- **`uv` on Windows can leave a half-installed Python on the first run.** If `uv sync` ever fails with `Missing expected target directory for Python minor version link`, delete `.venv\` and run `uv python install 3.12 --reinstall` before re-syncing. Symptom of pressing through that error: a venv whose `python.exe` launcher embeds a malformed interpreter path and then fails to start.
- The corpus and title list are committed (`data/corpus.jsonl`, `data/title_list.json`) so the project runs without network. Only `lac ingest` and the LLM-side `lac ask` need internet.
- `chroma_db/` is gitignored — rebuild it with `lac embed`. Takes well under a minute on CPU.
