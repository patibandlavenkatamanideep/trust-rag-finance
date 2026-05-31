"""LLM-backed synthesizer — grounded, fully-cited, schema-validated, or abstain.

Activates when an LLM provider + key are configured (see synthesis.model). Until
then the factory falls back to the no-API ExtractiveSynthesizer, so the project
runs without any key. The model is constrained to emit CitedAnswer JSON; invalid
output -> abstain (never emit an unvalidated answer).
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from shared.schemas import CitedAnswer, Confidence, RetrievedSource

from synthesis.model import LLMClient
from synthesis.prompts import SYNTHESIS_PROMPT
from synthesis.safety import screen_input


def _format_sources(sources: list[RetrievedSource]) -> str:
    blocks = []
    for s in sources:
        head = f"[{s.source_id}] {s.document_title}"
        if s.section:
            head += f" — {s.section}"
        if s.page is not None:
            head += f" (p.{s.page})"
        blocks.append(f"{head}\n{s.text}")
    return "\n\n".join(blocks)


_SCHEMA_HINT = (
    'Return ONLY JSON: {"answer": str, "claims": [{"text": str, "source_ids": [str], '
    '"supported": bool}], "citations": [{"source_id": str, "document_title": str, '
    '"section": str|null, "page": int|null}], "abstained": bool, '
    '"abstain_reason": str|null}. Every claim must cite >=1 source_id that appears '
    "in the sources above. If the sources do not support an answer, set abstained=true."
)


class LLMSynthesizer:
    """Implements shared.interfaces.Synthesizer using an LLMClient."""

    certified = True  # a real model judges relevance; band may reach high (gated by judge)

    def __init__(self, client: LLMClient, max_tokens: int = 1024) -> None:
        self.client = client
        self.max_tokens = max_tokens

    def synthesize(self, query: str, sources: list[RetrievedSource]) -> CitedAnswer:
        screen = screen_input(query)
        if screen.blocked:
            return self._abstain(screen.message or "Out of scope.", screen.reason or "blocked")
        if not sources:
            return self._abstain(
                "I couldn't find this in the research corpus.", "insufficient_context"
            )

        user = (
            f"SOURCES:\n{_format_sources(sources)}\n\n"
            f"QUESTION: {query}\n\n{_SCHEMA_HINT}"
        )
        try:
            raw = self.client.complete(SYNTHESIS_PROMPT.text, user, self.max_tokens)
            answer = self._parse(raw)
        except (ValidationError, json.JSONDecodeError, ValueError):
            return self._abstain(
                "The answer could not be validated against the source schema.",
                "schema_validation_failed",
            )
        except Exception:  # noqa: BLE001 - provider/network errors -> safe abstain
            return self._abstain("The synthesis service was unavailable.", "synthesis_error")

        valid_ids = {s.source_id for s in sources}
        if not answer.abstained and not self._all_cited(answer, valid_ids):
            return self._abstain(
                "The generated answer cited sources outside the retrieved set.",
                "invalid_citations",
            )
        return answer

    @staticmethod
    def _parse(raw: str) -> CitedAnswer:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no JSON object in model output")
        data = json.loads(raw[start : end + 1])
        answer = CitedAnswer.model_validate(
            {**data, "confidence": data.get("confidence") or {"band": "medium"}}
        )
        return answer

    @staticmethod
    def _all_cited(answer: CitedAnswer, valid_ids: set[str]) -> bool:
        for claim in answer.claims:
            if not claim.source_ids or any(sid not in valid_ids for sid in claim.source_ids):
                return False
        return True

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
