# Retrieval evaluation

- Embedding model: `BAAI/bge-small-en-v1.5`
- Queries: 6 (5 answerable, 1 negative)
- K: 5

## Aggregate (answerable queries only)

| Metric | Value |
|---|---|
| Recall@5 | **1.000** |
| MRR | **0.850** |

## Answerable queries

| Query | Relevant | Rank of first relevant | Recall@5 | RR |
|---|---|---|---|---|
| Who invented the C programming language? | `c_(programming_language)` | 1 | 1.000 | 1.000 |
| language used for SAP business applications | `abap` | 1 | 1.000 | 1.000 |
| array programming language designed for financial applications | `a+_(programming_language)` | 1 | 1.000 | 1.000 |
| dependently typed functional language used for theorem proving | `agda_(programming_language)` | 4 | 1.000 | 0.250 |
| language designed at Ericsson for building concurrent telecommunication systems | `erlang_(programming_language)` | 1 | 1.000 | 1.000 |

## Negative queries (no relevant doc in corpus)

Top-1 score is the system's *confidence* on an unanswerable query — lower is better (less false confidence). The grounded prompt in `generate.ask` is what turns this signal into the fixed IDK sentence.

| Query | Top-1 doc_id | Top-1 score |
|---|---|---|
| What is the capital of France? | `caml` | 0.486 |

## Top hits per query

### Who invented the C programming language?

Relevant: `c_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.830 | `c_(programming_language)` (*) | C (programming language) |
| 2 | 0.706 | `b_(programming_language)` | B (programming language) |
| 3 | 0.705 | `language_h` | Language H |
| 4 | 0.703 | `darsimco` | DARSIMCO |
| 5 | 0.689 | `slip_(programming_language)` | SLIP (programming language) |

### language used for SAP business applications

Relevant: `abap`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.771 | `abap` (*) | ABAP |
| 2 | 0.697 | `synergy_dbl` | Synergy DBL |
| 3 | 0.689 | `general-purpose_programming_language` | General-purpose programming language |
| 4 | 0.686 | `dibol` | DIBOL |
| 5 | 0.685 | `k_(programming_language)` | K (programming language) |

### array programming language designed for financial applications

Relevant: `a+_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.823 | `a+_(programming_language)` (*) | A+ (programming language) |
| 2 | 0.760 | `k_(programming_language)` | K (programming language) |
| 3 | 0.754 | `refal` | Refal |
| 4 | 0.742 | `crystal_(programming_language)` | Crystal (programming language) |
| 5 | 0.726 | `j_(programming_language)` | J (programming language) |

### dependently typed functional language used for theorem proving

Relevant: `agda_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.739 | `refal` | Refal |
| 2 | 0.715 | `reversible_programming_language` | Reversible programming language |
| 3 | 0.701 | `clojure` | Clojure |
| 4 | 0.699 | `agda_(programming_language)` (*) | Agda (programming language) |
| 5 | 0.696 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |

### language designed at Ericsson for building concurrent telecommunication systems

Relevant: `erlang_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.740 | `erlang_(programming_language)` (*) | Erlang (programming language) |
| 2 | 0.713 | `e_(programming_language)` | E (programming language) |
| 3 | 0.687 | `structured_text` | Structured text |
| 4 | 0.674 | `caml` | Caml |
| 5 | 0.668 | `reversible_programming_language` | Reversible programming language |

### What is the capital of France?

Relevant: `(none — negative query)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.486 | `caml` | Caml |
| 2 | 0.451 | `nemerle` | Nemerle |
| 3 | 0.446 | `f_(programming_language)` | F (programming language) |
| 4 | 0.441 | `comal` | COMAL |
| 5 | 0.434 | `bliss` | BLISS |

