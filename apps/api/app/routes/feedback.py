"""POST /feedback — capture advisor verdict for the trust-build loop (S9).

used-as-is / edited / rejected / disputed. Disputed + edited later feed the
advisor-curated golden set. Phase 1 stores it on the audit record in memory.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.deps import get_audit

router = APIRouter(tags=["feedback"])

Verdict = Literal["used_as_is", "edited", "rejected", "disputed"]


class FeedbackRequest(BaseModel):
    query_id: str
    verdict: Verdict
    note: str | None = None


@router.post("/feedback")
def post_feedback(req: FeedbackRequest) -> dict[str, str]:
    audit = get_audit()
    record = audit.get(req.query_id)
    if record is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    # Append-only store: record the verdict alongside (does not mutate history).
    record["feedback"] = {"verdict": req.verdict, "note": req.note}
    return {"status": "recorded", "query_id": req.query_id}
