"""Cross-encoder reranker — lifts precision of the final top-k (helps groundedness).

Two implementations behind the Reranker seam:
* StubReranker — deterministic lexical-overlap scorer. Zero deps, reorders
  candidates by query/chunk token overlap. Good enough to wire + test the stage.
* CrossEncoderReranker — real sentence-transformers CrossEncoder (optional, [ml]).
"""

from __future__ import annotations

import re

from shared.config import Settings, get_settings
from shared.schemas import RetrievedSource

_WORD = re.compile(r"[a-z0-9]+")


def _overlap_score(query: str, text: str) -> float:
    q = set(_WORD.findall(query.lower()))
    if not q:
        return 0.0
    t = set(_WORD.findall(text.lower()))
    return len(q & t) / len(q)


class StubReranker:
    """Implements shared.interfaces.Reranker via lexical overlap."""

    def rerank(
        self, query: str, candidates: list[RetrievedSource], top_k: int
    ) -> list[RetrievedSource]:
        scored = sorted(
            candidates, key=lambda s: _overlap_score(query, s.text), reverse=True
        )
        return scored[:top_k]


class CrossEncoderReranker:
    """Real cross-encoder reranker (optional, lazy import)."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError(
                "RERANKER_PROVIDER=cross_encoder requires the 'ml' extra: "
                "pip install '.[ml]'"
            ) from exc
        self._model = CrossEncoder(model_name)

    def rerank(
        self, query: str, candidates: list[RetrievedSource], top_k: int
    ) -> list[RetrievedSource]:
        if not candidates:
            return []
        scores = self._model.predict([(query, c.text) for c in candidates])
        ranked = [c for _, c in sorted(zip(scores, candidates), key=lambda kv: kv[0], reverse=True)]
        return ranked[:top_k]


def get_reranker(settings: Settings | None = None):
    cfg = settings or get_settings()
    if cfg.reranker_provider == "cross_encoder":
        return CrossEncoderReranker()
    return StubReranker()
