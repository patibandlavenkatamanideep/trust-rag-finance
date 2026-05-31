"""Stub synthesizer: abstains when there is no evidence (safe default, S1).

This lets the full pipeline run before an LLM is wired. When sources exist it
echoes a minimal grounded shape so downstream verification has something to
check; the real generator replaces it in Phase 4.
"""

from __future__ import annotations

from shared.schemas import (
    Citation,
    CitedAnswer,
    Claim,
    Confidence,
    RetrievedSource,
)


class StubSynthesizer:
    """Implements shared.interfaces.Synthesizer."""

    def synthesize(self, query: str, sources: list[RetrievedSource]) -> CitedAnswer:
        if not sources:
            return CitedAnswer(
                answer="",
                claims=[],
                citations=[],
                confidence=Confidence(
                    band="abstain",
                    reason="No retrieved sources support an answer (stub synthesizer).",
                ),
                abstained=True,
                abstain_reason="insufficient_context",
            )

        # Minimal grounded placeholder: one claim per source, fully cited.
        claims = [
            Claim(text=s.text[:160], source_ids=[s.source_id], supported=True)
            for s in sources[:1]
        ]
        citations = [
            Citation(
                source_id=s.source_id,
                document_title=s.document_title,
                company=s.company,
                ticker=s.ticker,
                section=s.section,
                page=s.page,
            )
            for s in sources[:1]
        ]
        return CitedAnswer(
            answer=f"[stub] {sources[0].text[:160]} [{sources[0].source_id}]",
            claims=claims,
            citations=citations,
            confidence=Confidence(band="medium", reason="stub synthesizer output"),
            abstained=False,
        )
