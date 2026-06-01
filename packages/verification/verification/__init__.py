"""Verification: deterministic citation checks + groundedness judge + confidence.

The deterministic verifier (`verify_citations`) is REAL in Phase 1 — it is a
core differentiator and must never be skipped. The judge is stubbed until an LLM
is wired (Phase 5). Confidence is derived from system signals, never the model's
self-report.
"""

from verification.citation import verify_citations
from verification.confidence import score_confidence
from verification.judge import EntailmentJudge, LLMJudge, StubJudge, get_judge

__all__ = [
    "verify_citations",
    "score_confidence",
    "EntailmentJudge",
    "LLMJudge",
    "StubJudge",
    "get_judge",
]
