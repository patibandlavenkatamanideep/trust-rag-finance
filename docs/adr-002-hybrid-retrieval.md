# ADR-002 — Hybrid Retrieval

**Status:** Accepted.

## Context

Financial documents are dense with exact identifiers — tickers (AAPL), CUSIPs, fund names,
accounting terms, section titles, regulatory codes. Pure semantic (dense vector) search
silently fails on these: it retrieves "vibes-similar" passages but misses the exact-term
match an advisor's question hinges on.

## Decision

Use **hybrid retrieval**: BM25 lexical + dense semantic, fused with **Reciprocal Rank
Fusion (RRF)**, then **cross-encoder reranking** to a small top-k that feeds synthesis.

- **MVP engine:** pgvector (dense) + a BM25 library (lexical) + RRF in application code
  ([packages/retrieval/retrieval/fusion.py](../packages/retrieval/retrieval/fusion.py),
  already implemented and unit-tested).
- **Enterprise engine:** OpenSearch, which provides BM25 + dense kNN + RRF + filtering in one
  engine. The `Retriever` seam is identical, so this is an adapter swap.

## Rationale

- BM25 anchors on exact terms; dense recovers paraphrase/semantic matches; RRF combines them
  without tuning weights and rewards documents both methods agree on (which also feeds the
  **retrieval-agreement** confidence signal).
- The cross-encoder rerank lifts precision of the final top-k, which is what the
  groundedness/citation bars depend on.

## Consequences

- Retrieval agreement (lexical ∩ dense) becomes a free, deterministic confidence input.
- Slightly more moving parts than a single vector store, but each is behind the one
  `Retriever` interface.
- RRF is deterministic and parameter-light (`k=60` default), so retrieval results are
  reproducible for eval and audit.
