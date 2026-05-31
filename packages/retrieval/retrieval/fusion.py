"""Reciprocal Rank Fusion — combines lexical and dense result lists.

RRF is deterministic and parameter-light: score(d) = sum_l 1/(k + rank_l(d)).
This is real (not a stub) because it has no external dependency and is unit
tested — the fusion contract is part of the retrieval boundary.
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse multiple ranked id-lists into one, highest score first.

    Args:
        ranked_lists: each inner list is ids ordered best-first for one method.
        k: RRF constant; larger k flattens the contribution of top ranks.

    Returns:
        (doc_id, score) pairs sorted by descending fused score.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
