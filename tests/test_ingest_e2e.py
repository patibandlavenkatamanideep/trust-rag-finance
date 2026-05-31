"""End-to-end ingestion: a file on disk becomes searchable chunks in the store."""

from pathlib import Path

from shared.embeddings import StubEmbedder
from ingestion.pipeline import ingest_document, withdraw_document
from retrieval.store import SqliteChunkStore


def test_ingest_then_supersede_new_version(tmp_path: Path):
    store = SqliteChunkStore("sqlite:///:memory:")
    embedder = StubEmbedder(dim=64)

    v1 = tmp_path / "AAPL_10-K_2024.txt"
    v1.write_text(
        "Services\n\nApple services revenue grew across all geographic segments.\n",
        encoding="utf-8",
    )
    res1 = ingest_document(v1, store, embedder)
    assert res1.chunks_written >= 1
    assert res1.document_id == "AAPL_10-K_2024"
    assert all(c["embedding"] is not None for c in store.all_current())

    # Ingest a v2 of the same logical document -> v1 chunks superseded.
    v2 = tmp_path / "AAPL_10-K_2024_v2.txt"
    v2.write_text(
        "Services\n\nApple services revenue grew even faster this year.\n",
        encoding="utf-8",
    )
    res2 = ingest_document(v2, store, embedder)
    assert res2.superseded >= 1
    versions = {c["version"] for c in store.all_current()}
    assert versions == {"v2"}


def test_withdraw_excludes_document(tmp_path: Path):
    store = SqliteChunkStore("sqlite:///:memory:")
    f = tmp_path / "NVDA_10-K_2024.txt"
    f.write_text("Risk Factors\n\nSupply constraints could harm results.\n", encoding="utf-8")
    ingest_document(f, store, StubEmbedder(dim=64))
    assert len(store.all_current()) >= 1

    withdraw_document("NVDA_10-K_2024", store)
    assert store.all_current() == []
