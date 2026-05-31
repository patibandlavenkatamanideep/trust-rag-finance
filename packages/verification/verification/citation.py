"""Deterministic citation verifier — the structural guard against confident-wrong.

Checks (CLAUDE.md):
  * every claim has >=1 source id;
  * every cited source id exists in the retrieved set;
  * the answer cites nothing outside the retrieval set;
  * each claim has lexical overlap with at least one cited chunk.

This is deterministic (no LLM) so its result is auditable and reproducible.
"""

from __future__ import annotations

import re

from shared.schemas import CitedAnswer, RetrievedSource, VerificationResult

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _has_lexical_support(claim_text: str, chunk_text: str, min_overlap: int = 2) -> bool:
    """Cheap, explainable overlap check. Phase 5 adds a semantic/entailment pass."""
    claim_tokens = _tokens(claim_text)
    if not claim_tokens:
        return False
    overlap = claim_tokens & _tokens(chunk_text)
    # Require either an absolute floor or a reasonable fraction of the claim.
    return len(overlap) >= min(min_overlap, len(claim_tokens)) and (
        len(overlap) / len(claim_tokens) >= 0.15
    )


def verify_citations(
    answer: CitedAnswer, sources: list[RetrievedSource]
) -> VerificationResult:
    valid_ids = {s.source_id for s in sources}
    source_text = {s.source_id: s.text for s in sources}

    invalid_citations: list[str] = []
    unsupported_claims: list[str] = []

    # Any citation pointing outside the retrieved set is invalid.
    for cite in answer.citations:
        if cite.source_id not in valid_ids:
            invalid_citations.append(cite.source_id)

    for claim in answer.claims:
        if not claim.source_ids:
            unsupported_claims.append(claim.text)
            continue
        # All referenced ids must exist...
        unknown = [sid for sid in claim.source_ids if sid not in valid_ids]
        if unknown:
            invalid_citations.extend(unknown)
            unsupported_claims.append(claim.text)
            continue
        # ...and at least one cited chunk must lexically support the claim.
        supported = any(
            _has_lexical_support(claim.text, source_text[sid])
            for sid in claim.source_ids
        )
        if not supported:
            unsupported_claims.append(claim.text)

    total_claims = len(answer.claims)
    supported_count = total_claims - len(unsupported_claims)
    citation_validity = (
        1.0 if not answer.citations else 1.0 - len(set(invalid_citations)) / max(
            len(answer.citations), 1
        )
    )

    return VerificationResult(
        citation_validity=round(max(citation_validity, 0.0), 4),
        unsupported_claims=unsupported_claims,
        invalid_citations=sorted(set(invalid_citations)),
        all_claims_supported=(total_claims > 0 and supported_count == total_claims)
        or (total_claims == 0 and answer.abstained),
    )
