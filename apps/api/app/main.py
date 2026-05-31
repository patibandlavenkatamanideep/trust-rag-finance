"""FastAPI entrypoint for the query-service."""

from __future__ import annotations

from fastapi import FastAPI

from shared.config import get_settings
from shared.logging import configure_logging

from app.routes import audit, eval as eval_routes, feedback, health, query

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
app.include_router(feedback.router)
app.include_router(audit.router)
app.include_router(eval_routes.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": cfg.app_name, "status": "ok", "docs": "/docs"}
