"""Confidence scoring from SYSTEM signals (never the model's self-report).

Combines: citation validity (deterministic), groundedness (judge), retrieval
agreement, and number of supporting chunks. Conservative to start (D12): bands
favor abstention/verify. Tunable as calibration proves out.
"""

from __future__ import annotations

from shared.config import get_settings
from shared.schemas import (
    Confidence,
    ConfidenceBand,
    CitedAnswer,
    RetrievedSource,
    VerificationResult,
)


def _band(
    *, citation_validity: float, groundedness: float, n_sources: int, abstained: bool
) -> ConfidenceBand:
    if abstained:
        return "abstain"
    cfg = get_settings()
    if (
        citation_validity >= 1.0
        and groundedness >= cfg.high_confidence_groundedness
        and n_sources >= 1
    ):
        return "high"
    if citation_validity >= 1.0 and groundedness >= 0.85:
        return "medium"
    return "low"


def score_confidence(
    answer: CitedAnswer,
    sources: list[RetrievedSource],
    verification: VerificationResult,
    groundedness: float,
    retrieval_agreement: float = 0.0,
) -> Confidence:
    band = _band(
        citation_validity=verification.citation_validity,
        groundedness=groundedness,
        n_sources=len(sources),
        abstained=answer.abstained,
    )
    reasons = []
    if answer.abstained:
        reasons.append(answer.abstain_reason or "abstained")
    if verification.unsupported_claims:
        reasons.append(f"{len(verification.unsupported_claims)} unsupported claim(s)")
    if verification.invalid_citations:
        reasons.append(f"{len(verification.invalid_citations)} invalid citation(s)")
    if not reasons:
        reasons.append(f"groundedness={groundedness}, citation_validity={verification.citation_validity}")

    return Confidence(
        band=band,
        retrieval_agreement=round(retrieval_agreement, 4),
        citation_validity=verification.citation_validity,
        groundedness_score=round(groundedness, 4),
        reason="; ".join(reasons),
    )
