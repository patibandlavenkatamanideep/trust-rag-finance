"""Embedding adapters + factory. Implements shared.interfaces.EmbeddingModel.

The SAME embedder must run at ingest and query time (D9). Two implementations:

* StubEmbedder — deterministic, pure-Python, hash-based. Zero dependencies, runs
  anywhere, reproducible. Good enough to wire and test the pipeline; it captures
  exact-token overlap (a real signal for finance terms) but not deep semantics.
* SentenceTransformerEmbedder — real semantic vectors, optional (`pip install
  '.[ml]'`). Selected when EMBEDDING_PROVIDER=sentence_transformers.

Swap in OpenAI/Voyage/Bedrock adapters here later; callers depend only on the
EmbeddingModel Protocol.
"""

from __future__ import annotations

import hashlib
import math
import re

from shared.config import Settings, get_settings

_WORD = re.compile(r"[a-z0-9]+")


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


class StubEmbedder:
    """Deterministic bag-of-hashed-tokens embedding, L2-normalized.

    Each token is hashed into a bucket and contributes weight; cosine similarity
    then reflects shared vocabulary. Deterministic across runs and machines.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _WORD.findall(text.lower()):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            bucket = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[bucket] += sign
        return _l2_normalize(vec)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class SentenceTransformerEmbedder:
    """Real sentence-transformers embeddings (optional, lazy import)."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "EMBEDDING_PROVIDER=sentence_transformers requires the 'ml' extra: "
                "pip install '.[ml]'"
            ) from exc
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]


def get_embedder(settings: Settings | None = None):
    """Return the EmbeddingModel selected by config."""
    cfg = settings or get_settings()
    if cfg.embedding_provider == "sentence_transformers":
        return SentenceTransformerEmbedder(cfg.embedding_model_name)
    # 'stub' (default) and not-yet-implemented providers fall back to the stub.
    return StubEmbedder(dim=cfg.embedding_dim)
