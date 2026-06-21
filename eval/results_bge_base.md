# Retrieval evaluation

- Embedding model: `BAAI/bge-base-en-v1.5`
- Queries: 6 (5 answerable, 1 negative)
- K: 5
- LLM (for `--ask`): `claude-haiku-4-5`

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

**Claude answer:**

> C was created by Dennis Ritchie [c_(programming_language)]. It was originally developed at Bell Labs by Ritchie between 1972 and 1973 [c_(programming_language)].

**Citations:** `c_(programming_language)`

### language used for SAP business applications

Relevant: `abap`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.750 | `abap` (*) | ABAP |
| 2 | 0.671 | `dibol` | DIBOL |
| 3 | 0.648 | `scriptol` | Scriptol |
| 4 | 0.638 | `general-purpose_programming_language` | General-purpose programming language |
| 5 | 0.628 | `synergy_dbl` | Synergy DBL |

**Claude answer:**

> ABAP (Advanced Business Application Programming) is the language used for SAP business applications [abap]. It is positioned alongside Java as the language for programming the SAP NetWeaver Application Server, which is part of the SAP NetWeaver platform for building business applications [abap].

**Citations:** `abap`

### array programming language designed for financial applications

Relevant: `a+_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.780 | `a+_(programming_language)` (*) | A+ (programming language) |
| 2 | 0.736 | `k_(programming_language)` | K (programming language) |
| 3 | 0.690 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |
| 4 | 0.688 | `fx-87` | FX-87 |
| 5 | 0.686 | `apl_(programming_language)` | APL (programming language) |

**Claude answer:**

> A+ is a high-level, interactive, interpreted array programming language designed for numerically intensive applications, especially those found in financial applications [a+_(programming_language)].
> 
> Additionally, K is a proprietary array processing programming language that serves as the foundation for kdb+, an in-memory, column-based database, and other related financial products [k_(programming_language)].

**Citations:** `a+_(programming_language)`, `k_(programming_language)`

### dependently typed functional language used for theorem proving

Relevant: `agda_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.723 | `fx-87` | FX-87 |
| 2 | 0.717 | `agda_(programming_language)` (*) | Agda (programming language) |
| 3 | 0.674 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |
| 4 | 0.669 | `refal` | Refal |
| 5 | 0.662 | `cameleon_(programming_language)` | Cameleon (programming language) |

**Claude answer:**

> Based on the provided context, **Agda** is a dependently typed functional programming language used for theorem proving [agda_(programming_language)]. Agda is a proof assistant based on the propositions-as-types paradigm (Curry–Howard correspondence), and proofs are written in a functional programming style [agda_(programming_language)].

**Citations:** `agda_(programming_language)`

### language designed at Ericsson for building concurrent telecommunication systems

Relevant: `erlang_(programming_language)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.709 | `erlang_(programming_language)` (*) | Erlang (programming language) |
| 2 | 0.670 | `e_(programming_language)` | E (programming language) |
| 3 | 0.669 | `janus_(time-reversible_computing_programming_language)` | Janus (time-reversible computing programming language) |
| 4 | 0.669 | `fx-87` | FX-87 |
| 5 | 0.669 | `hermes_(programming_language)` | Hermes (programming language) |

**Claude answer:**

> Erlang is the language designed at Ericsson for building concurrent telecommunication systems. It is a general-purpose, concurrent, functional high-level programming language that was originally proprietary software within Ericsson, developed by Joe Armstrong, Robert Virding, and Mike Williams in 1986 [erlang_(programming_language)]. The Erlang runtime system is specifically designed for distributed, fault-tolerant, and highly available systems, making it well-suited for telecommunications applications. It was released as free and open-source software in 1998 and is supported and maintained by the Open Telecom Platform (OTP) product unit at Ericsson [erlang_(programming_language)].

**Citations:** `erlang_(programming_language)`

### What is the capital of France?

Relevant: `(none — negative query)`

| Rank | Score | doc_id | Title |
|---|---|---|---|
| 1 | 0.412 | `python_(programming_language)` | Python (programming language) |
| 2 | 0.400 | `charm_(programming_language)` | Charm (programming language) |
| 3 | 0.398 | `caml` | Caml |
| 4 | 0.388 | `comal` | COMAL |
| 5 | 0.387 | `go_(programming_language)` | Go (programming language) |

**Claude answer:**

> I don't know based on the provided context.

**Citations:** _(none extracted)_

