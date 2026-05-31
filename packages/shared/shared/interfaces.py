"""Abstract seams (Protocols) for the pipeline.

These are the `Retriever` / `Synthesizer` / `Store` boundaries from ADR-001.
Concrete adapters (OpenSearch, pgvector, Bedrock/Anthropic, Postgres) implement
them and are wired only in `apps/api`. Swapping infra = swapping an adapter, not
a rewrite. Phase 1 ships stub adapters so the skeleton runs end-to-end.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from shared.schemas import (
    CitedAnswer,
    GoldenQuestion,
    RetrievedSource,
    VerificationResult,
)


@runtime_checkable
class EmbeddingModel(Protocol):
    """Same model must be used at ingest and query time (D9)."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class Retriever(Protocol):
    """Hybrid BM25 + dense + RRF + rerank, behind one interface (ADR-002)."""

    def retrieve(
        self, query: str, top_k: int, filters: dict[str, Any] | None = None
    ) -> list[RetrievedSource]: ...


@runtime_checkable
class Reranker(Protocol):
    def rerank(
        self, query: str, candidates: list[RetrievedSource], top_k: int
    ) -> list[RetrievedSource]: ...


@runtime_checkable
class Synthesizer(Protocol):
    """Produces a schema-valid CitedAnswer or abstains."""

    def synthesize(self, query: str, sources: list[RetrievedSource]) -> CitedAnswer: ...


@runtime_checkable
class GroundednessJudge(Protocol):
    """LLM-as-judge: a signal, never the source of truth (CLAUDE.md)."""

    def score(self, answer: CitedAnswer, sources: list[RetrievedSource]) -> float: ...


@runtime_checkable
class CitationVerifier(Protocol):
    """Deterministic check that every claim is backed by a retrieved chunk."""

    def verify(
        self, answer: CitedAnswer, sources: list[RetrievedSource]
    ) -> VerificationResult: ...


@runtime_checkable
class AuditStore(Protocol):
    """Append-only audit seam (D24/D28). MVP = plain table; later = WORM/SIEM."""

    def append(self, record: dict[str, Any]) -> str: ...

    def get(self, query_id: str) -> dict[str, Any] | None: ...


@runtime_checkable
class GoldenStore(Protocol):
    def load(self) -> list[GoldenQuestion]: ...
