"""GET /audit/{query_id} — retrieve the provenance trail for one query."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.deps import get_audit

router = APIRouter(tags=["audit"])


@router.get("/audit/{query_id}")
def get_audit_record(query_id: str) -> dict:
    record = get_audit().get(query_id)
    if record is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return record
