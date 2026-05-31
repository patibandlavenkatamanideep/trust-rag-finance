"""Retrieval-service: hybrid BM25 + dense + RRF + rerank (ADR-002).

RRF fusion is a pure tested function. The HybridRetriever orchestrates lexical +
dense search over the ChunkStore, fuses, and reranks. Stub adapters remain for
tests and for running before an index exists.
"""

from retrieval.bm25 import BM25Index
from retrieval.dense import DenseIndex
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import StubReranker, get_reranker
from retrieval.store import SqliteChunkStore
from retrieval.stub import StubRetriever

__all__ = [
    "BM25Index",
    "DenseIndex",
    "reciprocal_rank_fusion",
    "HybridRetriever",
    "StubReranker",
    "get_reranker",
    "SqliteChunkStore",
    "StubRetriever",
]
