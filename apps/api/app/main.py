"""FastAPI entrypoint for the query-service."""

from __future__ import annotations

from fastapi import FastAPI

from shared.config import get_settings
from shared.logging import configure_logging

from app.routes import (
    audit,
    eval as eval_routes,
    feedback,
    health,
    query,
    retrieve,
)

cfg = get_settings()
configure_logging(cfg.log_level)

app = FastAPI(
    title=cfg.app_name,
    version="0.1.0",
    description="Evaluation-driven, read-only wealth research assistant. "
    "Cardinal failure to avoid: a confident wrong answer.",
)

app.include_router(health.router)
app.include_router(query.router)
app.include_router(retrieve.router)
app.include_router(feedback.router)
app.include_router(audit.router)
app.include_router(eval_routes.router)


@app.on_event("startup")
def _seed_corpus_if_empty() -> None:
    """Self-seed the index on boot when empty (Railway's filesystem is ephemeral).

    Controlled by AUTO_INGEST (default on). Idempotent: ingestion upserts by
    deterministic chunk id, so a warm volume is left untouched.
    """
    import os

    if os.environ.get("AUTO_INGEST", "1") not in ("1", "true", "True"):
        return
    from pathlib import Path

    from shared.embeddings import get_embedder
    from ingestion.pipeline import ingest_path
    from retrieval.store import SqliteChunkStore

    from app.deps import get_retriever

    store = SqliteChunkStore(cfg.chunk_store_url)
    docs = Path("data/sample_docs")
    if store.count() == 0 and docs.exists():
        ingest_path(docs, store, get_embedder(cfg))
        get_retriever().refresh()  # rebuild the in-process index
    store.close()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": cfg.app_name, "status": "ok", "docs": "/docs"}
