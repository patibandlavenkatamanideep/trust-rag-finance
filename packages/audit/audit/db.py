"""Database-agnostic hash-chained audit ledger (SQLite + Postgres) via SQLAlchemy.

Same implementation runs on SQLite (local default) and Postgres (Railway, durable
across restarts) — only the connection URL changes. Append-only + tamper-evident:
each row stores payload + prev_hash + row_hash = sha256(canonical_json(payload) +
prev_hash); `verify_chain()` recomputes and pinpoints the first break. This is the
production form of the audit ledger (D24); WORM/SIEM remains a later adapter (D28).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
)

GENESIS = "0" * 64

_metadata = MetaData()
_audit = Table(
    "audit",
    _metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True),
    Column("query_id", String(128), unique=True, nullable=False),
    Column("payload", Text, nullable=False),
    Column("prev_hash", String(64), nullable=False),
    Column("row_hash", String(64), nullable=False),
    Column("created_at", String(64)),
)


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(payload_json: str, prev_hash: str) -> str:
    return hashlib.sha256((payload_json + prev_hash).encode("utf-8")).hexdigest()


class SqlAuditStore:
    """Implements shared.interfaces.AuditStore on any SQLAlchemy-supported DB."""

    def __init__(self, url: str = "sqlite:///data/index/audit.db") -> None:
        # future=True for 2.0-style; pool_pre_ping for resilient Postgres connections.
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self._engine = create_engine(
            url, future=True, pool_pre_ping=True, connect_args=connect_args
        )
        _metadata.create_all(self._engine)

    def _last_hash(self, conn) -> str:
        row = conn.execute(
            select(_audit.c.row_hash).order_by(_audit.c.seq.desc()).limit(1)
        ).first()
        return row[0] if row else GENESIS

    def append(self, record: dict[str, Any]) -> str:
        query_id = record["query_id"]
        payload_json = _canonical(record)
        with self._engine.begin() as conn:
            exists = conn.execute(
                select(_audit.c.seq).where(_audit.c.query_id == query_id)
            ).first()
            if exists:
                raise ValueError(f"audit is append-only; {query_id} already exists")
            prev = self._last_hash(conn)
            conn.execute(
                insert(_audit).values(
                    query_id=query_id,
                    payload=payload_json,
                    prev_hash=prev,
                    row_hash=_hash(payload_json, prev),
                    created_at=str(record.get("created_at", datetime.now(timezone.utc).isoformat())),
                )
            )
        return query_id

    def get(self, query_id: str) -> dict[str, Any] | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(_audit.c.payload, _audit.c.row_hash, _audit.c.seq).where(
                    _audit.c.query_id == query_id
                )
            ).first()
        if not row:
            return None
        payload = json.loads(row[0])
        payload["_seq"] = row[2]
        payload["_row_hash"] = row[1]
        return payload

    def all(self) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            rows = conn.execute(select(_audit.c.payload).order_by(_audit.c.seq)).all()
        return [json.loads(r[0]) for r in rows]

    def verify_chain(self) -> dict[str, Any]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    _audit.c.seq, _audit.c.query_id, _audit.c.payload,
                    _audit.c.prev_hash, _audit.c.row_hash,
                ).order_by(_audit.c.seq)
            ).all()
        prev = GENESIS
        for seq, query_id, payload, prev_hash, row_hash in rows:
            expected = _hash(payload, prev)
            if prev_hash != prev or row_hash != expected:
                return {"valid": False, "rows": len(rows),
                        "broken_at_seq": seq, "broken_query_id": query_id}
            prev = row_hash
        return {"valid": True, "rows": len(rows), "head_hash": prev}

    def count(self) -> int:
        with self._engine.connect() as conn:
            return conn.execute(select(func.count()).select_from(_audit)).scalar() or 0

    def close(self) -> None:
        self._engine.dispose()
