"""Live ingestion routes (Phase 9 — always live & fresh).

POST /documents/ingest  -> (re)scan the corpus dir and index new/updated reports
POST /ingest/webhook    -> publish a single report OR withdraw one, near-real-time
GET  /corpus/status     -> freshness view: counts, versions, latest publish dates

All paths are idempotent (deterministic chunk ids) and version-aware (new version
supersedes old). After any change the in-process retriever index is refreshed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared.config import get_settings
from shared.embeddings import get_embedder
from ingestion.loaders import discover_documents
from ingestion.pipeline import ingest_document, ingest_path, withdraw_document

from app.deps import get_chunk_store, get_retriever

router = APIRouter(tags=["ingest"])


def _refresh_index() -> None:
    retriever = get_retriever()
    if hasattr(retriever, "refresh"):
        retriever.refresh()


def _corpus_path() -> Path:
    cfg = get_settings()
    primary = Path(cfg.corpus_dir)
    # Use the primary corpus only if it has *loadable* documents (a lone README
    # doesn't count); otherwise fall back to the seeded sample corpus.
    if primary.exists() and discover_documents(primary):
        return primary
    return Path(cfg.fallback_corpus_dir)


# --------------------------------------------------------------------------- #
class IngestResponse(BaseModel):
    documents: int
    chunks_written: int
    superseded: int
    store_total: int


@router.post("/documents/ingest", response_model=IngestResponse)
def ingest_corpus() -> IngestResponse:
    """Scan the corpus dir and index everything (idempotent re-ingest)."""
    cfg = get_settings()
    store = get_chunk_store()
    results = ingest_path(_corpus_path(), store, get_embedder(cfg))
    _refresh_index()
    return IngestResponse(
        documents=len(results),
        chunks_written=sum(r.chunks_written for r in results),
        superseded=sum(r.superseded for r in results),
        store_total=store.count(),
    )


# --------------------------------------------------------------------------- #
class WebhookRequest(BaseModel):
    action: Literal["publish", "withdraw"]
    document_id: str = Field(..., description="Logical report id, e.g. AAPL_10-K_2024")
    ticker: Optional[str] = None
    document_type: Optional[str] = None
    year: Optional[str] = None
    text: Optional[str] = Field(None, description="Report body (required for publish)")


@router.post("/ingest/webhook")
def ingest_webhook(req: WebhookRequest) -> dict:
    """Near-real-time path: publish a new report or withdraw an existing one.

    Withdrawal is compliance-critical (a retracted report must leave retrieval
    immediately), so it is exposed as a push event per the freshness SLA (D7).
    """
    cfg = get_settings()
    store = get_chunk_store()

    if req.action == "withdraw":
        n = withdraw_document(req.document_id, store)
        _refresh_index()
        if n == 0:
            raise HTTPException(status_code=404, detail=f"no current chunks for {req.document_id}")
        return {"status": "withdrawn", "document_id": req.document_id, "chunks_excluded": n}

    # publish
    if not req.text:
        raise HTTPException(status_code=422, detail="publish requires 'text'")
    # The document_id is the authoritative report name and carries the metadata
    # convention (TICKER_DOCTYPE_YEAR[_vN]); the chunker re-extracts ticker/type/
    # year/version from it. Persist to the corpus dir so the nightly scan sees it
    # too, then ingest immediately.
    corpus = Path(cfg.corpus_dir)
    corpus.mkdir(parents=True, exist_ok=True)
    path = corpus / f"{req.document_id}.txt"
    path.write_text(req.text, encoding="utf-8")

    result = ingest_document(path, store, get_embedder(cfg))
    _refresh_index()
    return {
        "status": "published",
        "document_id": result.document_id,
        "version": result.version,
        "chunks_written": result.chunks_written,
        "superseded": result.superseded,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------- #
@router.get("/corpus/status")
def corpus_status() -> dict:
    """Freshness view over the current index."""
    store = get_chunk_store()
    chunks = store.all_current()
    by_doc: dict[str, dict] = {}
    for c in chunks:
        d = by_doc.setdefault(
            c["document_id"],
            {"ticker": c.get("ticker"), "document_type": c.get("document_type"),
             "version": c.get("version"), "publish_date": c.get("publish_date"), "chunks": 0},
        )
        d["chunks"] += 1
    return {
        "corpus_dir": str(_corpus_path()),
        "total_chunks": store.count(),
        "current_chunks": len(chunks),
        "documents": len(by_doc),
        "by_document": by_doc,
    }
