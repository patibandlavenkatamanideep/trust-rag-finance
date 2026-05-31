"""Liveness/readiness."""

from __future__ import annotations

from fastapi import APIRouter

from shared.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    cfg = get_settings()
    return {
        "status": "healthy",
        "service": cfg.app_name,
        "environment": cfg.environment,
        "llm_provider": cfg.llm_provider,
    }
