"""Retrieval-service: hybrid BM25 + dense + RRF + rerank (ADR-002).

Phase 1 ships RRF fusion (pure function, tested) and a stub Retriever so the
pipeline runs. Phase 3 wires real BM25, dense, and the cross-encoder reranker.
"""

from retrieval.fusion import reciprocal_rank_fusion
from retrieval.stub import StubRetriever

__all__ = ["reciprocal_rank_fusion", "StubRetriever"]
