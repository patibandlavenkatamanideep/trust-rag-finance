"""Phase 3 retrieval: BM25, dense, and the full hybrid pipeline over a store."""

from pathlib import Path

from shared.embeddings import StubEmbedder
from ingestion.pipeline import ingest_document
from retrieval.bm25 import BM25Index
from retrieval.dense import DenseIndex
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import StubReranker
from retrieval.store import SqliteChunkStore


def test_bm25_ranks_exact_term_first():
    # Needs >2 docs so the matched term has positive IDF (small-corpus effect).
    idx = BM25Index(
        ["c1", "c2", "c3"],
        [
            "Apple services revenue grew across segments",
            "Tesla automotive margins fell this quarter",
            "Microsoft cloud infrastructure spending increased",
        ],
    )
    hits = idx.search("services revenue", top_n=5)
    assert hits[0][0] == "c1"


def test_dense_index_finds_self():
    e = StubEmbedder(dim=64)
    texts = ["risk factors and supply constraints", "services revenue growth"]
    embs = e.embed(texts)
    idx = DenseIndex(["c1", "c2"], embs)
    hits = idx.search(e.embed(["supply constraints risk"])[0], top_n=2)
    assert hits[0][0] == "c1"


def _seed_store(tmp_path: Path) -> tuple[SqliteChunkStore, StubEmbedder]:
    store = SqliteChunkStore("sqlite:///:memory:")
    embedder = StubEmbedder(dim=128)
    aapl = tmp_path / "AAPL_10-K_2024.txt"
    aapl.write_text(
        "Services\n\nApple services revenue grew across all geographic segments.\n\n"
        "Risk Factors\n\nApp Store practices face regulatory scrutiny.\n",
        encoding="utf-8",
    )
    nvda = tmp_path / "NVDA_10-K_2024.txt"
    nvda.write_text(
        "Risk Factors\n\nNVIDIA faces supply constraints and customer concentration.\n",
        encoding="utf-8",
    )
    ingest_document(aapl, store, embedder)
    ingest_document(nvda, store, embedder)
    return store, embedder


def test_hybrid_retrieves_relevant_and_assigns_source_ids(tmp_path: Path):
    store, embedder = _seed_store(tmp_path)
    r = HybridRetriever(store, embedder, StubReranker())
    sources = r.retrieve("What does Apple say about services revenue?", top_k=3)

    assert sources, "expected at least one source"
    assert sources[0].source_id == "source_1"
    top = sources[0]
    assert top.ticker == "AAPL"
    assert "services" in top.text.lower()
    assert top.retrieval_method == "hybrid_rrf_rerank"


def test_ticker_filter_excludes_other_companies(tmp_path: Path):
    store, embedder = _seed_store(tmp_path)
    r = HybridRetriever(store, embedder, StubReranker())
    # Query names Apple -> NVDA chunks must not appear.
    sources = r.retrieve("Apple risk factors", top_k=5)
    assert sources
    assert all(s.ticker == "AAPL" for s in sources)


def test_empty_store_returns_nothing():
    store = SqliteChunkStore("sqlite:///:memory:")
    r = HybridRetriever(store, StubEmbedder(dim=64), StubReranker())
    assert r.retrieve("anything", top_k=5) == []
