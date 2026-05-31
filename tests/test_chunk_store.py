from retrieval.store import SqliteChunkStore


def _rec(chunk_id, document_id="doc_1", status="current", version="v1"):
    return {
        "chunk_id": chunk_id, "document_id": document_id, "document_title": "t",
        "company": "Apple Inc.", "ticker": "AAPL", "document_type": "10-K",
        "publish_date": "2024", "section_title": "Risk Factors", "page": 1,
        "text": "some text", "version": version, "source_path": "p",
        "status": status, "embedding": [0.1, 0.2, 0.3],
    }


def test_upsert_is_idempotent():
    store = SqliteChunkStore("sqlite:///:memory:")
    store.upsert([_rec("c1"), _rec("c2")])
    store.upsert([_rec("c1")])  # same id again
    assert store.count() == 2
    got = store.get("c1")
    assert got["embedding"] == [0.1, 0.2, 0.3]


def test_supersede_excludes_from_current():
    store = SqliteChunkStore("sqlite:///:memory:")
    store.upsert([_rec("c1"), _rec("c2")])
    n = store.set_status("doc_1", "superseded")
    assert n == 2
    assert store.all_current() == []
    assert store.count() == 2  # rows kept for audit, just not current


def test_only_current_returned():
    store = SqliteChunkStore("sqlite:///:memory:")
    store.upsert([_rec("c1"), _rec("c2", status="withdrawn")])
    current = store.all_current()
    assert {c["chunk_id"] for c in current} == {"c1"}
