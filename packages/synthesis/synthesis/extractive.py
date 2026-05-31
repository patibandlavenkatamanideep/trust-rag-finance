"""Extractive synthesizer — grounded answers with NO LLM (works without an API).

Strategy:
  1. Screen the input (advice / injection) -> abstain deterministically.
  2. Gate on relevance: how much of the query's content vocabulary is covered by
     the retrieved sources. Below a conservative threshold -> abstain ("couldn't
     find this") per S1 (abstention is a success state).
  3. Otherwise build the answer by extracting the most query-relevant sentences
     from the top sources, each carrying its [source_n] citation. Because the
     answer is verbatim from cited passages, citation verification passes by
     construction.

It does NOT certify "high" confidence — without a real judge the system can't be
sure the quoted passage truly *answers* the question (relevance != correctness),
so `certified=False` caps the band at medium. The LLM synthesizer (Phase 4) lifts
answer quality and, with the judge (Phase 5), can certify high.
"""

from __future__ import annotations

import re

from shared.schemas import (
    Citation,
    CitedAnswer,
    Claim,
    Confidence,
    RetrievedSource,
)

from synthesis.safety import screen_input

_WORD = re.compile(r"[a-z0-9]+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Common words that carry no retrieval signal; excluded from coverage scoring.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "by", "with", "at", "as", "it", "its", "this", "that",
    "what", "does", "do", "did", "say", "says", "said", "about", "how", "much",
    "their", "they", "from", "has", "have", "had", "company", "report", "tell",
    "me", "i", "we", "you", "your", "our", "can", "will", "would", "should",
}


def _content_words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS and len(w) > 1}


def _best_sentences(query_terms: set[str], text: str, limit: int = 2) -> list[str]:
    sentences = _SENT_SPLIT.split(text.strip())
    scored = []
    for s in sentences:
        overlap = len(query_terms & _content_words(s))
        if overlap:
            scored.append((overlap, s.strip()))
    scored.sort(key=lambda kv: kv[0], reverse=True)
    return [s for _, s in scored[:limit]]


class ExtractiveSynthesizer:
    """Implements shared.interfaces.Synthesizer without any LLM call."""

    #: Pipeline reads this to cap confidence (no judge => not certified high).
    certified = False

    def __init__(self, coverage_threshold: float = 0.34, max_sources: int = 2) -> None:
        self.coverage_threshold = coverage_threshold
        self.max_sources = max_sources

    def synthesize(self, query: str, sources: list[RetrievedSource]) -> CitedAnswer:
        screen = screen_input(query)
        if screen.blocked:
            return self._abstain(screen.message or "Out of scope.", screen.reason or "blocked")

        if not sources:
            return self._abstain(
                "I couldn't find this in the research corpus.", "insufficient_context"
            )

        query_terms = _content_words(query)
        if not query_terms:
            return self._abstain("The question is too vague to ground.", "ambiguous_query")

        # Relevance gate: coverage of query terms across the top sources.
        top = sources[: self.max_sources]
        covered = set()
        for s in top:
            covered |= query_terms & _content_words(s.text)
        coverage = len(covered) / len(query_terms)
        if coverage < self.coverage_threshold:
            return self._abstain(
                "The retrieved research does not sufficiently address this question.",
                "insufficient_support",
            )

        # Build an extractive, fully-cited answer from the top sources.
        claims: list[Claim] = []
        citations: list[Citation] = []
        answer_parts: list[str] = []
        for s in top:
            sents = _best_sentences(query_terms, s.text, limit=1)
            if not sents:
                continue
            quote = sents[0]
            claims.append(Claim(text=quote, source_ids=[s.source_id], supported=True))
            citations.append(
                Citation(
                    source_id=s.source_id,
                    document_title=s.document_title,
                    company=s.company,
                    ticker=s.ticker,
                    section=s.section,
                    page=s.page,
                )
            )
            answer_parts.append(f"{quote} [{s.source_id}]")

        if not claims:
            return self._abstain(
                "The retrieved research does not sufficiently address this question.",
                "insufficient_support",
            )

        return CitedAnswer(
            answer=" ".join(answer_parts),
            claims=claims,
            citations=citations,
            confidence=Confidence(
                band="medium",
                reason=f"extractive answer; query-term coverage={coverage:.2f}",
            ),
            abstained=False,
        )

    @staticmethod
    def _abstain(message: str, reason: str) -> CitedAnswer:
        return CitedAnswer(
            answer=message,
            claims=[],
            citations=[],
            confidence=Confidence(band="abstain", reason=reason),
            abstained=True,
            abstain_reason=reason,
        )
