"""SQLite-backed ChunkStore. Implements shared.interfaces.ChunkStore.

Zero external dependencies (stdlib sqlite3) so ingestion + retrieval run with no
infrastructure. Embeddings are stored as JSON; Phase 3 does brute-force cosine
over `all_current()`. A Postgres+pgvector adapter can implement the same Protocol
later for scale — callers depend only on the interface.

Idempotent: `upsert` is keyed on chunk_id (deterministic, D21), so re-ingesting a
document replaces its chunks rather than duplicating them.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_COLUMNS = [
    "chunk_id", "document_id", "document_title", "company", "ticker",
    "document_type", "publish_date", "section_title", "page", "text",
    "version", "source_path", "status", "embedding",
]


def _sqlite_path(url: str) -> str:
    """Accept 'sqlite:///rel/path.db', 'sqlite:////abs/path.db', or a bare path."""
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):]
    return url


class SqliteChunkStore:
    def __init__(self, url: str = "sqlite:///data/index/chunks.db") -> None:
        self.path = _sqlite_path(url)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: a uvicorn worker handles requests on threads
        # distinct from the startup thread that builds the index. SQLite serializes
        # access internally; our access is read-heavy + low-concurrency for the pilot.
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_title TEXT,
                company TEXT,
                ticker TEXT,
                document_type TEXT,
                publish_date TEXT,
                section_title TEXT,
                page INTEGER,
                text TEXT NOT NULL,
                version TEXT,
                source_path TEXT,
                status TEXT NOT NULL DEFAULT 'current',
                embedding TEXT
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_doc ON chunks(document_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON chunks(status)")
        self._conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["embedding"] = json.loads(d["embedding"]) if d.get("embedding") else None
        return d

    def upsert(self, records: list[dict[str, Any]]) -> int:
        rows = []
        for r in records:
            emb = r.get("embedding")
            rows.append(
                tuple(
                    json.dumps(emb) if col == "embedding" else r.get(col)
                    for col in _COLUMNS
                )
            )
        placeholders = ", ".join("?" for _ in _COLUMNS)
        cols = ", ".join(_COLUMNS)
        self._conn.executemany(
            f"INSERT OR REPLACE INTO chunks ({cols}) VALUES ({placeholders})", rows
        )
        self._conn.commit()
        return len(rows)

    def all_current(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM chunks WHERE status = 'current'")
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def get(self, chunk_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def set_status(self, document_id: str, status: str) -> int:
        cur = self._conn.execute(
            "UPDATE chunks SET status = ? WHERE document_id = ?", (status, document_id)
        )
        self._conn.commit()
        return cur.rowcount

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
