"""FastAPI entrypoint for the query-service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from shared.config import get_settings
from shared.logging import configure_logging, get_logger

from app.routes import (
    audit,
    eval as eval_routes,
    feedback,
    health,
    ingest,
    query,
    retrieve,
)

cfg = get_settings()
configure_logging(cfg.log_level)
log = get_logger("startup")


def _seed_corpus_if_empty() -> None:
    """Self-seed the index on boot when empty (Railway's filesystem is ephemeral).

    Controlled by AUTO_INGEST (default on). Scans the live corpus dir, falling
    back to the bundled sample docs. Idempotent (deterministic chunk ids), and
    fault-tolerant — seeding must never block readiness.
    """
    if os.environ.get("AUTO_INGEST", "1") not in ("1", "true", "True"):
        return
    from shared.embeddings import get_embedder
    from ingestion.pipeline import ingest_path

    from app.deps import get_chunk_store, get_retriever

    try:
        store = get_chunk_store()
        if store.count() > 0:
            return
        primary = Path(cfg.corpus_dir)
        docs = primary if (primary.exists() and any(primary.iterdir())) else Path(cfg.fallback_corpus_dir)
        if docs.exists():
            results = ingest_path(docs, store, get_embedder(cfg))
            retriever = get_retriever()
            if hasattr(retriever, "refresh"):
                retriever.refresh()
            log.info("auto-ingest complete",
                     extra={"fields": {"dir": str(docs), "documents": len(results),
                                       "chunks": store.count()}})
    except Exception as exc:  # noqa: BLE001 - never let seeding block readiness
        log.error("auto-ingest failed; serving with empty corpus",
                  extra={"fields": {"error": str(exc)}})


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_corpus_if_empty()
    yield


app = FastAPI(
    title=cfg.app_name,
    version="0.1.0",
    description="Evaluation-driven, read-only wealth research assistant. "
    "Cardinal failure to avoid: a confident wrong answer.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(query.router)
app.include_router(retrieve.router)
app.include_router(ingest.router)
app.include_router(feedback.router)
app.include_router(audit.router)
app.include_router(eval_routes.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": cfg.app_name, "status": "ok", "docs": "/docs"}
