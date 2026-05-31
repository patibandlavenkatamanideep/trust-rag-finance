"""POST /query — run a question through the linear RAG pipeline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from shared.schemas import QueryResponse

from app.deps import get_audit, get_pipeline
from app.pipeline import QueryPipeline

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


@router.post("/query", response_model=QueryResponse)
def post_query(
    req: QueryRequest, pipeline: QueryPipeline = Depends(get_pipeline)
) -> QueryResponse:
    return pipeline.run(req.query)


@router.get("/query/{query_id}")
def get_query(query_id: str) -> dict:
    record = get_audit().get(query_id)
    if record is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return record
