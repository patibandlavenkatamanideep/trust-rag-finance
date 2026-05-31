"""Audit record schema. Mirrors the audit fields in CLAUDE.md."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    query_id: str
    user_query: str
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    answer: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence_band: str = "abstain"
    confidence_reason: str = ""
    model_name: str = "stub"
    prompt_version: str = "synthesis@v1"
    citation_verification: dict[str, Any] = Field(default_factory=dict)
    groundedness_result: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    feedback: Optional[str] = None
