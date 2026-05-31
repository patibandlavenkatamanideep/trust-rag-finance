"""Groundedness judge (LLM-as-judge). Stubbed until an LLM is wired (Phase 5).

The judge is a SIGNAL, combined with deterministic checks — never the source of
truth. The real judge must use a different model than synthesis (anti-
JudgeOverfitting, D9) and be calibrated to >=80% advisor agreement before trust.
"""

from __future__ import annotations

from shared.schemas import CitedAnswer, RetrievedSource


class StubJudge:
    """Implements shared.interfaces.GroundednessJudge.

    Returns a conservative proxy: 0.0 on abstain, else derives a score from the
    deterministic claim-support flags so the skeleton has a plausible number.
    """

    def score(self, answer: CitedAnswer, sources: list[RetrievedSource]) -> float:
        if answer.abstained or not answer.claims:
            return 0.0
        supported = sum(1 for c in answer.claims if c.supported)
        return round(supported / len(answer.claims), 4)
