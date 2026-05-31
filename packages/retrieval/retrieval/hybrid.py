"""HybridRetriever — BM25 + dense + RRF + rerank over the ChunkStore.

Implements shared.interfaces.Retriever. The pipeline:
  1. (optional) metadata pre-filter from the parsed query (ticker)
  2. BM25 top-N  +  dense top-N  (same embedder as ingest, D9)
  3. RRF fuse the two ranked lists
  4. cross-encoder rerank the fused candidates -> top-k
  5. assign source_ids + provenance -> list[RetrievedSource]

Indexes are built lazily from `store.all_current()` and cached; call `refresh()`
after ingesting new documents in the same process.
"""

from __future__ import annotations

from typing import Any

from shared.config import get_settings
from shared.interfaces import ChunkStore, EmbeddingModel, Reranker
from shared.logging import get_logger
from shared.schemas import RetrievedSource

from retrieval.bm25 import BM25Index
from retrieval.dense import DenseIndex
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.query_parse import parse_query

log = get_logger("retrieval")


class HybridRetriever:
    def __init__(
        self,
        store: ChunkStore,
        embedder: EmbeddingModel,
        reranker: Reranker,
        top_n: int | None = None,
        rrf_k: int | None = None,
    ) -> None:
        cfg = get_settings()
        self.store = store
        self.embedder = embedder
        self.reranker = reranker
        self.top_n = top_n or cfg.retrieval_top_n
        self.rrf_k = rrf_k or cfg.rrf_k
        self._records: dict[str, dict[str, Any]] = {}
        self._bm25: BM25Index | None = None
        self._dense: DenseIndex | None = None
        self._built = False

    # -- index lifecycle ---------------------------------------------------- #
    def _build(self) -> None:
        chunks = self.store.all_current()
        self._records = {c["chunk_id"]: c for c in chunks}
        ids = list(self._records.keys())
        self._bm25 = BM25Index(ids, [self._records[i]["text"] for i in ids])
        self._dense = DenseIndex(
            ids, [self._records[i].get("embedding") or [] for i in ids]
        )
        self._built = True
        log.info("retrieval index built", extra={"fields": {"chunks": len(ids)}})

    def refresh(self) -> None:
        self._built = False

    def _ensure(self) -> None:
        if not self._built:
            self._build()

    # -- retrieval ---------------------------------------------------------- #
    def retrieve(
        self, query: str, top_k: int, filters: dict[str, Any] | None = None
    ) -> list[RetrievedSource]:
        self._ensure()
        assert self._bm25 is not None and self._dense is not None

        ticker = (filters or {}).get("ticker") or parse_query(query).ticker

        bm25_hits = self._bm25.search(query, self.top_n)
        dense_hits = self._dense.search(self.embedder.embed([query])[0], self.top_n)

        def _eligible(cid: str) -> bool:
            if ticker is None:
                return True
            return (self._records.get(cid, {}).get("ticker") or "").upper() == ticker

        bm25_ids = [cid for cid, _ in bm25_hits if _eligible(cid)]
        dense_ids = [cid for cid, _ in dense_hits if _eligible(cid)]

        fused = reciprocal_rank_fusion([bm25_ids, dense_ids], k=self.rrf_k)
        if not fused:
            return []

        # Build candidate sources for the top fused chunks, then rerank.
        candidate_pool = max(top_k * 3, top_k)
        candidates = [
            self._to_source(cid, score) for cid, score in fused[:candidate_pool]
        ]
        reranked = self.reranker.rerank(query, candidates, top_k)

        # Assign stable source_ids in final order.
        for i, src in enumerate(reranked, start=1):
            src.source_id = f"source_{i}"
        return reranked

    def _to_source(self, chunk_id: str, score: float) -> RetrievedSource:
        r = self._records[chunk_id]
        return RetrievedSource(
            source_id="pending",
            chunk_id=chunk_id,
            document_id=r["document_id"],
            document_title=r.get("document_title") or r["document_id"],
            company=r.get("company"),
            ticker=r.get("ticker"),
            document_type=r.get("document_type"),
            section=r.get("section_title"),
            page=r.get("page"),
            version=r.get("version") or "v1",
            score=round(score, 6),
            retrieval_method="hybrid_rrf_rerank",
            text=r["text"],
        )
