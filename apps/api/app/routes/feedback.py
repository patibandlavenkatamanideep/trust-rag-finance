"""POST /feedback — capture advisor verdict for the trust-build loop (S9).

used-as-is / edited / rejected / disputed. Disputed + edited later feed the
advisor-curated golden set. Recorded as its own append-only ledger event.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    if audit.get(req.query_id) is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    # Append-only ledger: feedback is a NEW chained event referencing the original
    # query, never a mutation of the past record (that would break the hash chain).
    feedback_id = f"fb_{uuid.uuid4()}"
    audit.append(
        {
            "query_id": feedback_id,
            "type": "feedback",
            "ref_query_id": req.query_id,
            "verdict": req.verdict,
            "note": req.note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"status": "recorded", "query_id": req.query_id, "feedback_id": feedback_id}
