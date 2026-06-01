"""Audit routes — provenance trail + tamper-evidence (D24).

GET /audit/verify   -> recompute the hash chain, report integrity (tamper check)
GET /audit/recent   -> recent ledger entries (query trace view feed)
GET /audit/{id}      -> one query's full provenance record

Note: literal routes are declared before /{query_id} so they aren't captured.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.deps import get_audit

router = APIRouter(tags=["audit"])


@router.get("/audit/verify")
def verify_chain() -> dict:
    audit = get_audit()
    if not hasattr(audit, "verify_chain"):
        return {"valid": None, "detail": "audit store is not a hash-chained ledger"}
    return audit.verify_chain()


@router.get("/audit/recent")
def recent(limit: int = Query(20, ge=1, le=200)) -> dict:
    audit = get_audit()
    records = audit.all() if hasattr(audit, "all") else []
    return {"count": len(records), "records": records[-limit:][::-1]}


@router.get("/audit/{query_id}")
def get_audit_record(query_id: str) -> dict:
    record = get_audit().get(query_id)
    if record is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return record
