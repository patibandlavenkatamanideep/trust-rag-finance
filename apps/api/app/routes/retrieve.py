"""POST /retrieve — return ranked source chunks for a query (debug/demo of Phase 3).

Exposes the retrieval stage directly so you can see hybrid search + rerank
working, separate from synthesis. POST /retrieve/refresh rebuilds the in-process
index after ingesting new documents.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.config import get_settings
from shared.interfaces import Retriever
from shared.schemas import RetrievedSource

from app.deps import get_retriever

router = APIRouter(tags=["retrieve"])


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int | None = None


@router.post("/retrieve", response_model=list[RetrievedSource])
def post_retrieve(
    req: RetrieveRequest, retriever: Retriever = Depends(get_retriever)
) -> list[RetrievedSource]:
    top_k = req.top_k or get_settings().retrieval_top_k
    return retriever.retrieve(req.query, top_k=top_k)


@router.post("/retrieve/refresh")
def refresh_index(retriever: Retriever = Depends(get_retriever)) -> dict[str, str]:
    # HybridRetriever exposes refresh(); guard for stub retrievers.
    if hasattr(retriever, "refresh"):
        retriever.refresh()
        return {"status": "refreshed"}
    return {"status": "noop"}
