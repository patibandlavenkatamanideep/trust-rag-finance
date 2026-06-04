"""Groundedness judges — score how well an answer is supported by its sources.

The judge is a SIGNAL, combined with deterministic citation checks; never the
sole source of truth. Three implementations behind the GroundednessJudge seam:

* EntailmentJudge (default) — deterministic, model-independent. Independently
  re-checks each claim against the text of its cited chunk (does not trust the
  synthesizer's self-reported `supported` flag). Because it shares no model with
  synthesis, it structurally cannot collude with the generator (anti-
  JudgeOverfitting, D9).
* LLMJudge (optional) — an LLM scores groundedness. Should use a different model
  than synthesis; returns a calibrated score in [0, 1].
* StubJudge (legacy) — trusts the claim flags; kept for tests / fallback.
"""

from __future__ import annotations

import json
import re

from shared.schemas import CitedAnswer, RetrievedSource

_WORD = re.compile(r"[a-z0-9]+")

# Function words carry no grounding signal; counting them inflates the denominator
# and unfairly penalizes paraphrase. Score on CONTENT words only.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was",
    "were", "be", "been", "by", "with", "at", "as", "it", "its", "this", "that", "these",
    "those", "from", "has", "have", "had", "their", "they", "them", "which", "such",
    "including", "include", "includes", "various", "other", "also", "can", "could", "will",
    "would", "may", "might", "across", "all", "more", "than", "into", "over", "company",
    "companys", "s",
}


def _stem(token: str) -> str:
    """Tiny deterministic stemmer so grew/growth, regulatory/regulation, etc. match."""
    for suffix in ("ing", "edly", "ed", "ly", "ies", "es", "s", "ment", "tion", "ation"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _content_stems(text: str) -> set[str]:
    return {_stem(t) for t in _WORD.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1}


def _support_ratio(claim_text: str, chunk_text: str) -> float:
    """Fraction of the claim's content stems present in the chunk (proxy entailment).

    Stopword-filtered + stemmed so a paraphrase that preserves the facts scores
    high, while a fabricated claim (different content words) still scores low. This
    is the deterministic, model-independent groundedness proxy; swap LLMJudge for a
    semantic check when a separate judge model is available.
    """
    claim = _content_stems(claim_text)
    if not claim:
        return 0.0
    return len(claim & _content_stems(chunk_text)) / len(claim)


class EntailmentJudge:
    """Implements shared.interfaces.GroundednessJudge, deterministically."""

    def __init__(self, support_threshold: float = 0.5) -> None:
        self.support_threshold = support_threshold

    def score(self, answer: CitedAnswer, sources: list[RetrievedSource]) -> float:
        if answer.abstained or not answer.claims:
            return 0.0
        by_id = {s.source_id: s.text for s in sources}
        per_claim: list[float] = []
        for claim in answer.claims:
            best = max(
                (_support_ratio(claim.text, by_id.get(sid, "")) for sid in claim.source_ids),
                default=0.0,
            )
            per_claim.append(best)
        # Groundedness = mean per-claim support, but a single weak claim drags it
        # down (conservative, per S1): use the min-blended mean.
        mean = sum(per_claim) / len(per_claim)
        worst = min(per_claim)
        return round(0.5 * mean + 0.5 * worst, 4)


class LLMJudge:
    """LLM-as-judge. Returns a groundedness score in [0, 1]; abstains-safe on error."""

    _PROMPT = (
        "You are a strict grounding judge for a financial research assistant. "
        "Given an ANSWER and the SOURCES it cites, decide what fraction of the "
        "answer's factual content is directly supported by the sources. Penalize "
        "any claim that overstates or is not in the sources. Return ONLY JSON: "
        '{"groundedness": <float 0..1>, "unsupported": [<str>], "overstates": <bool>}.'
    )

    def __init__(self, client) -> None:  # client: synthesis.model.LLMClient
        self.client = client

    def score(self, answer: CitedAnswer, sources: list[RetrievedSource]) -> float:
        if answer.abstained or not answer.claims:
            return 0.0
        src = "\n\n".join(f"[{s.source_id}] {s.text}" for s in sources)
        user = f"SOURCES:\n{src}\n\nANSWER:\n{answer.answer}"
        try:
            raw = self.client.complete(self._PROMPT, user, max_tokens=512)
            start, end = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[start : end + 1])
            return max(0.0, min(1.0, float(data.get("groundedness", 0.0))))
        except Exception:  # noqa: BLE001 - judge failure must not crash the pipeline
            return 0.0


class StubJudge:
    """Legacy: trusts the synthesizer's claim flags. Kept for tests / fallback."""

    def score(self, answer: CitedAnswer, sources: list[RetrievedSource]) -> float:
        if answer.abstained or not answer.claims:
            return 0.0
        supported = sum(1 for c in answer.claims if c.supported)
        return round(supported / len(answer.claims), 4)


def get_judge(settings=None):
    """Return the configured judge. Default = deterministic EntailmentJudge."""
    from shared.config import get_settings

    cfg = settings or get_settings()
    if cfg.judge_provider == "llm":
        from synthesis.model import get_llm_client

        client = get_llm_client(cfg)
        if client is not None:
            return LLMJudge(client)
    if cfg.judge_provider == "stub":
        return StubJudge()
    return EntailmentJudge()
