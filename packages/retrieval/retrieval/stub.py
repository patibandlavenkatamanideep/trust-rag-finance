"""Stub retriever: keeps the skeleton runnable before indexes exist.

Returns nothing, which correctly drives the pipeline to ABSTAIN (the safe
default per S1). Swap for an OpenSearch/pgvector adapter in Phase 3 — the
`Retriever` Protocol is the only contract callers depend on.
"""

from __future__ import annotations

from typing import Any

from shared.schemas import RetrievedSource


class StubRetriever:
    """Implements shared.interfaces.Retriever."""

    def retrieve(
        self, query: str, top_k: int, filters: dict[str, Any] | None = None
    ) -> list[RetrievedSource]:
        return []
