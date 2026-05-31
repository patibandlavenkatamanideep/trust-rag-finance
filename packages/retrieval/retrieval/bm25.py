"""BM25 lexical index — anchors retrieval on exact terms (tickers, codes, names).

Pure-lexical complement to dense search; finance queries hinge on exact tokens
that embeddings blur (AAPL, 10-K, "services revenue"). Built in-memory over the
current chunks; fine for a pilot corpus, swap for OpenSearch at scale.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


class BM25Index:
    def __init__(self, chunk_ids: list[str], texts: list[str]) -> None:
        self.chunk_ids = chunk_ids
        self._bm25 = BM25Okapi([tokenize(t) for t in texts]) if texts else None

    def search(self, query: str, top_n: int) -> list[tuple[str, float]]:
        """Return up to top_n (chunk_id, score), best first, positive scores only."""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(zip(self.chunk_ids, scores), key=lambda kv: kv[1], reverse=True)
        return [(cid, float(s)) for cid, s in ranked[:top_n] if s > 0.0]
