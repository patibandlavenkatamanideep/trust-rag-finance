"""Dense semantic index — brute-force cosine over stored embeddings.

Embeddings are L2-normalized at ingest, so cosine == dot product. Brute force is
fine for a pilot corpus (hundreds–thousands of chunks); a real vector index
(pgvector / OpenSearch kNN) implements the same search contract at scale.
"""

from __future__ import annotations

import numpy as np


class DenseIndex:
    def __init__(self, chunk_ids: list[str], embeddings: list[list[float]]) -> None:
        self.chunk_ids = chunk_ids
        self._matrix = np.asarray(embeddings, dtype=np.float32) if embeddings else None

    def search(self, query_vec: list[float], top_n: int) -> list[tuple[str, float]]:
        if self._matrix is None or self._matrix.size == 0:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        sims = self._matrix @ q  # cosine, since both sides are normalized
        order = np.argsort(-sims)[:top_n]
        return [(self.chunk_ids[i], float(sims[i])) for i in order]
