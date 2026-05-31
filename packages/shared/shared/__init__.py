"""Shared kernel: schemas, config, logging, and provider-neutral interfaces.

Everything in TrustRAG Finance depends inward on this package. It holds no
infrastructure — only the contracts (Pydantic schemas + Protocols) that the
service packages implement. Concrete adapters are wired in `apps/api` only.
"""

from shared.schemas import (
    Citation,
    CitedAnswer,
    Claim,
    Confidence,
    ConfidenceBand,
    ExpectedBehavior,
    GoldenQuestion,
    RetrievedSource,
    VerificationResult,
)

__all__ = [
    "Citation",
    "CitedAnswer",
    "Claim",
    "Confidence",
    "ConfidenceBand",
    "ExpectedBehavior",
    "GoldenQuestion",
    "RetrievedSource",
    "VerificationResult",
]
