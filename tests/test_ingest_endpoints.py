"""Live ingestion endpoints (Phase 9): publish/withdraw/status, near-real-time.

Tests the route handlers directly with a temp in-memory store, so no server,
lifespan, or settings-cache juggling is needed.
"""

from pathlib import Path

import app.routes.ingest as ing
from shared.config import Settings
from retrieval.store import SqliteChunkStore


class _FakeRetriever:
    refreshed = 0

    def refresh(self) -> None:
        self.refreshed += 1


def _wire(monkeypatch, tmp_path: Path) -> tuple:
    store = SqliteChunkStore("sqlite:///:memory:")
    retriever = _FakeRetriever()
    monkeypatch.setattr(ing, "get_chunk_store", lambda: store)
    monkeypatch.setattr(ing, "get_retriever", lambda: retriever)
    monkeypatch.setattr(ing, "get_settings", lambda: Settings(corpus_dir=str(tmp_path / "reports")))
    return store, retriever


def test_webhook_publish_then_withdraw(monkeypatch, tmp_path):
    store, retriever = _wire(monkeypatch, tmp_path)

    pub = ing.ingest_webhook(ing.WebhookRequest(
        action="publish", document_id="AAPL_10-K_2025", ticker="AAPL",
        document_type="10-K", year="2025",
        text="Services\n\nApple services revenue grew strongly across all segments.",
    ))
    assert pub["status"] == "published"
    assert pub["chunks_written"] >= 1
    assert retriever.refreshed >= 1

    status = ing.corpus_status()
    assert status["documents"] >= 1
    assert status["current_chunks"] >= 1

    wd = ing.ingest_webhook(ing.WebhookRequest(action="withdraw", document_id="AAPL_10-K_2025"))
    assert wd["status"] == "withdrawn"
    assert ing.corpus_status()["current_chunks"] == 0


def test_publish_requires_text(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    from fastapi import HTTPException

    try:
        ing.ingest_webhook(ing.WebhookRequest(action="publish", document_id="X"))
        assert False, "expected 422"
    except HTTPException as exc:
        assert exc.status_code == 422


def test_new_version_supersedes(monkeypatch, tmp_path):
    store, _ = _wire(monkeypatch, tmp_path)
    base = dict(action="publish", ticker="NVDA", document_type="10-K")
    ing.ingest_webhook(ing.WebhookRequest(document_id="NVDA_10-K_2024", year="2024",
                                          text="Risk Factors\n\nSupply constraints persist.", **base))
    ing.ingest_webhook(ing.WebhookRequest(document_id="NVDA_10-K_2024_v2", year="2024",
                                          text="Risk Factors\n\nSupply constraints eased this year.", **base))
    versions = {c["version"] for c in store.all_current()}
    assert versions == {"v2"}
