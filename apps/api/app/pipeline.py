"""The linear, deterministic RAG pipeline (D4 — no agentic loop).

retrieve -> synthesize -> verify citations -> judge groundedness -> score
confidence -> abstain/flag -> audit. Low confidence routes to HITL; there is no
retry. This function depends only on the abstract seams it is handed.
"""

from __future__ import annotations

import time
import uuid

from shared.config import get_settings
from shared.interfaces import (
    AuditStore,
    CitationVerifier,
    GroundednessJudge,
    Retriever,
    Synthesizer,
)
from shared.logging import get_logger
from shared.schemas import QueryResponse
from synthesis.prompts import SYNTHESIS_PROMPT
from verification.confidence import score_confidence

log = get_logger("pipeline")


class QueryPipeline:
    def __init__(
        self,
        retriever: Retriever,
        synthesizer: Synthesizer,
        verifier: CitationVerifier,
        judge: GroundednessJudge,
        audit: AuditStore,
    ) -> None:
        self.retriever = retriever
        self.synthesizer = synthesizer
        self.verifier = verifier
        self.judge = judge
        self.audit = audit

    def run(self, query: str) -> QueryResponse:
        cfg = get_settings()
        query_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        # 1. retrieve
        sources = self.retriever.retrieve(query, top_k=cfg.retrieval_top_k)

        # 2. synthesize (schema-constrained; abstains on no evidence)
        answer = self.synthesizer.synthesize(query, sources)

        # 3. deterministic citation verification
        verification = self.verifier.verify(answer, sources)

        # 4. groundedness judge (signal only)
        groundedness = self.judge.score(answer, sources)

        # 5. confidence from system signals
        answer.confidence = score_confidence(
            answer, sources, verification, groundedness
        )
        # If deterministic checks failed, never present as high confidence.
        if verification.unsupported_claims or verification.invalid_citations:
            if answer.confidence.band == "high":
                answer.confidence.band = "low"

        latency_ms = int((time.perf_counter() - t0) * 1000)

        # 6. audit (append-only)
        self.audit.append(
            {
                "query_id": query_id,
                "user_query": query,
                "retrieved_chunk_ids": [s.chunk_id for s in sources],
                "answer": answer.answer,
                "citations": [c.model_dump() for c in answer.citations],
                "confidence_band": answer.confidence.band,
                "confidence_reason": answer.confidence.reason,
                "model_name": cfg.llm_provider,
                "prompt_version": f"{SYNTHESIS_PROMPT.id}@{SYNTHESIS_PROMPT.version}",
                "citation_verification": verification.model_dump(),
                "groundedness_result": {"score": groundedness},
                "latency_ms": latency_ms,
                "cost_usd": 0.0,
            }
        )

        log.info(
            "query handled",
            extra={
                "fields": {
                    "query_id": query_id,
                    "band": answer.confidence.band,
                    "n_sources": len(sources),
                    "latency_ms": latency_ms,
                }
            },
        )

        return QueryResponse(
            query_id=query_id,
            answer=answer.answer,
            claims=answer.claims,
            citations=answer.citations,
            confidence=answer.confidence,
            verification=verification,
            retrieved_sources=sources,
            abstained=answer.abstained,
        )
