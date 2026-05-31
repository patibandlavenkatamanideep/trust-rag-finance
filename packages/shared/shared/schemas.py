"""Core data contracts for the TrustRAG Finance pipeline.

These Pydantic models are the serialization boundary between every stage:
retrieval -> synthesis -> verification -> audit -> api. The synthesis LLM is
constrained to emit `CitedAnswer`; if it cannot, it must abstain.

Design rule (from CLAUDE.md): every factual claim maps to >=1 source id, or the
answer abstains. A fluent answer without valid citations is a failure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ConfidenceBand = Literal["high", "medium", "low", "abstain"]
ExpectedBehavior = Literal["answer", "abstain"]
RetrievalMethod = Literal["bm25", "dense", "hybrid_rrf", "hybrid_rrf_rerank"]


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
class RetrievedSource(BaseModel):
    """A single retrieved chunk with provenance, as returned by retrieval-service."""

    source_id: str = Field(..., description="Stable id within one answer, e.g. 'source_1'.")
    chunk_id: str
    document_id: str
    document_title: str
    company: Optional[str] = None
    ticker: Optional[str] = None
    document_type: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    version: str = "v1"
    score: float = 0.0
    retrieval_method: RetrievalMethod = "hybrid_rrf_rerank"
    text: str


# --------------------------------------------------------------------------- #
# Synthesis output contract
# --------------------------------------------------------------------------- #
class Claim(BaseModel):
    """One factual assertion in the answer, mapped to its supporting source ids."""

    text: str
    source_ids: list[str] = Field(default_factory=list)
    supported: bool = False


class Citation(BaseModel):
    source_id: str
    document_title: str
    company: Optional[str] = None
    ticker: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None


class Confidence(BaseModel):
    """System-derived confidence. Never the model's self-reported certainty."""

    band: ConfidenceBand
    retrieval_agreement: float = 0.0
    citation_validity: float = 0.0
    groundedness_score: float = 0.0
    reason: str = ""


class CitedAnswer(BaseModel):
    """The structured synthesis output. The only sanctioned answer shape."""

    answer: str
    claims: list[Claim] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence: Confidence
    abstained: bool = False
    abstain_reason: Optional[str] = None


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
class VerificationResult(BaseModel):
    """Deterministic citation-verifier output, computed before the judge runs."""

    citation_validity: float = 0.0
    unsupported_claims: list[str] = Field(default_factory=list)
    invalid_citations: list[str] = Field(default_factory=list)
    all_claims_supported: bool = False


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
class GoldenQuestion(BaseModel):
    id: str
    query: str
    expected_sources: list[str] = Field(default_factory=list)
    expected_sections: list[str] = Field(default_factory=list)
    expected_behavior: ExpectedBehavior = "answer"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    category: str = "general"
    ticker: Optional[str] = None


# --------------------------------------------------------------------------- #
# API response envelope
# --------------------------------------------------------------------------- #
class QueryResponse(BaseModel):
    query_id: str
    answer: str
    claims: list[Claim] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence: Confidence
    verification: VerificationResult
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    abstained: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
