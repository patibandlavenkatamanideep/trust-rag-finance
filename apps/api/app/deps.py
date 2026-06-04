"""Composition root: build the pipeline by wiring concrete adapters to seams.

Phase 3 wires the real HybridRetriever (BM25 + dense + RRF + rerank over the
SQLite ChunkStore) alongside the REAL deterministic citation verifier. Synthesis
+ judge are still stubs (Phase 4/5). Swapping in OpenSearch, an LLM, or Postgres
later means changing only this file.
"""

from __future__ import annotations

from functools import lru_cache

from audit import get_audit_store
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import get_reranker
from retrieval.store import SqliteChunkStore
from shared.config import get_settings
from shared.embeddings import get_embedder
from shared.interfaces import Retriever
from shared.schemas import CitedAnswer, RetrievedSource, VerificationResult
from synthesis import get_synthesizer
from synthesis.extractive import ExtractiveSynthesizer
from verification.citation import verify_citations
from verification.judge import get_judge

from app.pipeline import QueryPipeline


class _CitationVerifierAdapter:
    """Adapts the verify_citations function to the CitationVerifier Protocol."""

    def verify(
        self, answer: CitedAnswer, sources: list[RetrievedSource]
    ) -> VerificationResult:
        return verify_citations(answer, sources)


# Shared singletons (audit persists across requests; retriever caches its index).
_AUDIT = get_audit_store()


@lru_cache
def get_chunk_store() -> SqliteChunkStore:
    """Shared chunk store handle for live ingestion writes (Phase 9)."""
    return SqliteChunkStore(get_settings().chunk_store_url)


@lru_cache
def get_retriever() -> Retriever:
    cfg = get_settings()
    return HybridRetriever(
        store=get_chunk_store(),
        embedder=get_embedder(cfg),
        reranker=get_reranker(cfg),
    )


def _make_pipeline(synthesizer) -> QueryPipeline:
    return QueryPipeline(
        retriever=get_retriever(),
        synthesizer=synthesizer,
        verifier=_CitationVerifierAdapter(),
        judge=get_judge(),
        audit=_AUDIT,
    )


@lru_cache
def get_pipeline() -> QueryPipeline:
    """Live pipeline using the configured synthesizer (Gemini/Claude/.../extractive)."""
    return _make_pipeline(get_synthesizer())


@lru_cache
def get_eval_pipeline() -> QueryPipeline:
    """Eval pipeline forced to the no-API extractive synthesizer (zero cost).

    Use this for fast, free eval iteration. Pass live=True at the call site to
    eval the configured LLM provider instead.
    """
    return _make_pipeline(ExtractiveSynthesizer())


def get_audit():
    """The shared AuditStore (hash-chained SQLite by default)."""
    return _AUDIT
