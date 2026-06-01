"""Hash-chained, append-only SQLite audit ledger (D24 — tamper-evident).

Each row stores the audit payload plus `prev_hash` and `row_hash`, where
    row_hash = sha256(canonical_json(payload) + prev_hash)
and the first row chains from a fixed genesis hash. Any later edit to a payload
(or reordering/deletion) breaks the recomputed chain — `verify_chain()` detects
it. This is the MVP stand-in for WORM storage; the seam (AuditStore) is unchanged
so a true WORM/SIEM adapter is a later swap (D28).

Append-only by construction: no UPDATE/DELETE in the write path. Cross-thread
safe for the uvicorn worker model (check_same_thread=False).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _sqlite_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):]
    return url


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(payload_json: str, prev_hash: str) -> str:
    return hashlib.sha256((payload_json + prev_hash).encode("utf-8")).hexdigest()


class SqliteAuditStore:
    """Implements shared.interfaces.AuditStore with a hash-chained ledger."""

    def __init__(self, url: str = "sqlite:///data/index/audit.db") -> None:
        self.path = _sqlite_path(url)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                row_hash TEXT NOT NULL,
                created_at TEXT
            )
            """
        )
        self._conn.commit()

    def _last_hash(self) -> str:
        row = self._conn.execute("SELECT row_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        return row["row_hash"] if row else GENESIS

    def append(self, record: dict[str, Any]) -> str:
        query_id = record["query_id"]
        if self._conn.execute("SELECT 1 FROM audit WHERE query_id = ?", (query_id,)).fetchone():
            raise ValueError(f"audit is append-only; {query_id} already exists")
        payload_json = _canonical(record)
        prev = self._last_hash()
        row_hash = _hash(payload_json, prev)
        self._conn.execute(
            "INSERT INTO audit (query_id, payload, prev_hash, row_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (query_id, payload_json, prev, row_hash, str(record.get("created_at", ""))),
        )
        self._conn.commit()
        return query_id

    def get(self, query_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT payload, prev_hash, row_hash, seq FROM audit WHERE query_id = ?", (query_id,)
        ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload"])
        payload["_seq"] = row["seq"]
        payload["_row_hash"] = row["row_hash"]
        return payload

    def all(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT payload FROM audit ORDER BY seq").fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def verify_chain(self) -> dict[str, Any]:
        """Recompute the chain; report the first break if any (tamper detection)."""
        rows = self._conn.execute(
            "SELECT seq, query_id, payload, prev_hash, row_hash FROM audit ORDER BY seq"
        ).fetchall()
        prev = GENESIS
        for r in rows:
            expected = _hash(r["payload"], prev)
            if r["prev_hash"] != prev or r["row_hash"] != expected:
                return {
                    "valid": False,
                    "rows": len(rows),
                    "broken_at_seq": r["seq"],
                    "broken_query_id": r["query_id"],
                }
            prev = r["row_hash"]
        return {"valid": True, "rows": len(rows), "head_hash": prev}

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
