"""In-memory append-only audit store. Default for the Phase 1 skeleton.

Append-only by construction: `append` never overwrites; there is no update or
delete. The Postgres adapter (Phase 8) implements the same `AuditStore` Protocol
and adds durability + the hash-chain.
"""

from __future__ import annotations

from typing import Any


class InMemoryAuditStore:
    """Implements shared.interfaces.AuditStore."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []

    def append(self, record: dict[str, Any]) -> str:
        query_id = record["query_id"]
        if query_id in self._records:
            raise ValueError(f"audit is append-only; {query_id} already exists")
        self._records[query_id] = record
        self._order.append(query_id)
        return query_id

    def get(self, query_id: str) -> dict[str, Any] | None:
        return self._records.get(query_id)

    def all(self) -> list[dict[str, Any]]:
        return [self._records[q] for q in self._order]
