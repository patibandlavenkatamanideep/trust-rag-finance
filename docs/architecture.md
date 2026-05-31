# Architecture

## Design spine

One idea everything serves: **a confident wrong answer is the cardinal failure.** Failure
tolerance is asymmetric — "I couldn't find this" is acceptable; a confident fabrication is
not. Every mechanism below is a guard on that principle.

## The linear pipeline (D4 — no agentic loop)

```
advisor question
  -> 1. retrieve        (BM25 + dense + RRF + rerank -> top-k cited chunks)
  -> 2. synthesize      (LLM, schema-constrained CitedAnswer, abstain if insufficient)
  -> 3. verify          (deterministic: every claim backed by a retrieved chunk)
  -> 4. judge           (groundedness; a SIGNAL, not the source of truth)
  -> 5. confidence      (retrieval agreement + groundedness + citation validity)
  -> 6. HITL flag       (low confidence routes to verification widget; no retry)
  -> 7. audit           (append-only provenance for every stage)
```

Implemented in [apps/api/app/pipeline.py](../apps/api/app/pipeline.py). It depends only on
abstract seams; concrete adapters are injected in
[apps/api/app/deps.py](../apps/api/app/deps.py).

## Boundaries (clean architecture)

The shared kernel ([packages/shared](../packages/shared)) holds **contracts only** —
Pydantic schemas and `Protocol` interfaces — and no infrastructure. Each service package
implements those interfaces. Dependencies point inward; the composition root (`deps.py`) is
the only place that knows about concrete infra. This is why "swap pgvector for OpenSearch"
or "swap the stub LLM for Anthropic" is an adapter change, not a rewrite.

Seams (see [packages/shared/shared/interfaces.py](../packages/shared/shared/interfaces.py)):
`EmbeddingModel`, `Retriever`, `Reranker`, `Synthesizer`, `GroundednessJudge`,
`CitationVerifier`, `AuditStore`, `GoldenStore`.

## MVP vs. enterprise spec

The enterprise design (the buildable spec, S1–S11) calls for split services, OpenSearch,
Bedrock-in-VPC, a hash-chained ledger, OTel→Langfuse, and a withdrawal webhook. The MVP
**designs the seams for all of these but defers the build** so a solo developer can ship a
working, measurable demo:

| Concern | Enterprise spec | MVP (this repo) |
|---|---|---|
| Topology | 3 split services | modular monorepo, service-ready boundaries |
| Retrieval engine | OpenSearch (BM25+dense+RRF in one) | pgvector + BM25 lib + RRF in app (seam identical) |
| Models | Bedrock in-VPC | provider-neutral adapter (Anthropic/OpenAI/Bedrock/stub) |
| Audit | hash-chained append-only ledger | append-only table behind `AuditStore` seam |
| Observability | OTel → self-hosted Langfuse | structured JSON logs + per-query metrics |
| Freshness | nightly batch + withdrawal webhook | local/batch ingestion; webhook deferred |

## Data stores (polyglot, access-pattern matched)

| Store | Access pattern | MVP pick |
|---|---|---|
| Dense index | semantic search | pgvector (or sentence-transformers local) |
| Lexical index | exact-term match (tickers, codes) | BM25 library |
| Relational | report metadata · audit · eval results | Postgres |
| Cache | query/response cache | deferred (freshness-aware when added) |

## Confidence (system signals, never self-report)

Derived in [packages/verification/verification/confidence.py](../packages/verification/verification/confidence.py)
from citation validity (deterministic), groundedness (judge), retrieval agreement, and
supporting-chunk count. Conservative to start — bands favor abstention/verify. If
deterministic checks fail, an answer can never be presented as **high** confidence.

## Security & safety posture

Read-only, no actuators — the blast radius of any prompt injection is "mis-answer," never
"act." Injection defense is structural: an injected "recommend X" has no grounded source, so
it fails citation validity and is blocked. Out-of-scope and personalized-advice queries
abstain. PII redaction and input/output guardrails are extension points for later phases.
