"""Composition root: build the pipeline by wiring concrete adapters to seams.

Phase 1 wires stubs (StubRetriever / StubSynthesizer / StubJudge / in-memory
audit) plus the REAL deterministic citation verifier. Swapping in OpenSearch,
an LLM, or Postgres later means changing only this file.
"""

from __future__ import annotations

from functools import lru_cache

from audit.memory import InMemoryAuditStore
from retrieval.stub import StubRetriever
from shared.schemas import CitedAnswer, RetrievedSource, VerificationResult
from synthesis.stub import StubSynthesizer
from verification.citation import verify_citations
from verification.judge import StubJudge

from app.pipeline import QueryPipeline


class _CitationVerifierAdapter:
    """Adapts the verify_citations function to the CitationVerifier Protocol."""

    def verify(
        self, answer: CitedAnswer, sources: list[RetrievedSource]
    ) -> VerificationResult:
        return verify_citations(answer, sources)


# Shared singletons (audit must persist across requests within a process).
_AUDIT = InMemoryAuditStore()


@lru_cache
def get_pipeline() -> QueryPipeline:
    return QueryPipeline(
        retriever=StubRetriever(),
        synthesizer=StubSynthesizer(),
        verifier=_CitationVerifierAdapter(),
        judge=StubJudge(),
        audit=_AUDIT,
    )


def get_audit() -> InMemoryAuditStore:
    return _AUDIT
