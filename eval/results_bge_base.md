# Retrieval evaluation

- Embedding model: `BAAI/bge-base-en-v1.5`
- Queries: 6 (5 answerable, 1 negative)
- K: 5

## Aggregate (answerable queries only)

| Metric | Value |
|---|---|
| Recall@5 | **1.000** |
| MRR | **0.900** |

## Answerable queries

| Query | Relevant | Rank of first relevant | Recall@5 | RR |
|---|---|---|---|---|
| Who invented the C programming language? | `c_(programming_language)` | 1 | 1.000 | 1.000 |
| language used for SAP business applications | `abap` | 1 | 1.000 | 1.000 |
| array programming language designed for financial applications | `a+_(programming_language)` | 1 | 1.000 | 1.000 |
| dependently typed functional language used for theorem proving | `agda_(programming_language)` | 2 | 1.000 | 0.500 |
| language designed at Ericsson for building concurrent telecommunication systems | `erlang_(programming_language)` | 1 | 1.000 | 1.000 |

## Negative queries (no relevant doc in corpus)

Top-1 score is the system's *confidence* on an unanswerable query — lower is better (less false confidence). The grounded prompt in `generate.ask` is what turns this signal into the fixed IDK sentence.

| Query | Top-1 doc_id | Top-1 score |
|---|---|---|
| What is the capital of France? | `python_(programming_language)` | 0.412 |

## Top hits per query

### Who invented the C programming language?

Relevant: `c_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.795 | `c_(programming_language)` (*) | C (programming language) |
| 2 | 0.692 | `b_(programming_language)` | B (programming language) |
| 3 | 0.690 | `language_h` | Language H |
| 4 | 0.677 | `george_(programming_language)` | GEORGE (programming language) |
| 5 | 0.666 | `lisp_(programming_language)` | Lisp (programming language) |

### language used for SAP business applications

Relevant: `abap`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.750 | `abap` (*) | ABAP |
| 2 | 0.671 | `dibol` | DIBOL |
| 3 | 0.648 | `scriptol` | Scriptol |
| 4 | 0.638 | `general-purpose_programming_language` | General-purpose programming language |
| 5 | 0.628 | `synergy_dbl` | Synergy DBL |

### array programming language designed for financial applications

Relevant: `a+_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.780 | `a+_(programming_language)` (*) | A+ (programming language) |
| 2 | 0.736 | `k_(programming_language)` | K (programming language) |
| 3 | 0.690 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |
| 4 | 0.688 | `fx-87` | FX-87 |
| 5 | 0.686 | `apl_(programming_language)` | APL (programming language) |

### dependently typed functional language used for theorem proving

Relevant: `agda_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.723 | `fx-87` | FX-87 |
| 2 | 0.717 | `agda_(programming_language)` (*) | Agda (programming language) |
| 3 | 0.674 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |
| 4 | 0.669 | `refal` | Refal |
| 5 | 0.662 | `cameleon_(programming_language)` | Cameleon (programming language) |

### language designed at Ericsson for building concurrent telecommunication systems

Relevant: `erlang_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.709 | `erlang_(programming_language)` (*) | Erlang (programming language) |
| 2 | 0.670 | `e_(programming_language)` | E (programming language) |
| 3 | 0.669 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |
| 4 | 0.669 | `fx-87` | FX-87 |
| 5 | 0.669 | `hermes_(programming_language)` | Hermes (programming language) |

### What is the capital of France?

Relevant: `(none — negative query)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.412 | `python_(programming_language)` | Python (programming language) |
| 2 | 0.400 | `charm_(programming_language)` | Charm (programming language) |
| 3 | 0.398 | `caml` | Caml |
| 4 | 0.388 | `comal` | COMAL |
| 5 | 0.387 | `go_(programming_language)` | Go (programming language) |

