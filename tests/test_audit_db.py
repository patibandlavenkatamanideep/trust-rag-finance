"""SQLAlchemy audit ledger — same behavior on SQLite (here) and Postgres (Railway)."""

import json

from sqlalchemy import text

from audit.db import SqlAuditStore


def _rec(qid: str, answer: str = "a") -> dict:
    return {"query_id": qid, "user_query": "q", "answer": answer, "confidence_band": "high"}


def _store() -> SqlAuditStore:
    return SqlAuditStore("sqlite:///:memory:")


def test_append_get_and_count():
    s = _store()
    s.append(_rec("q1"))
    s.append(_rec("q2"))
    assert s.count() == 2
    got = s.get("q1")
    assert got["user_query"] == "q" and got["_row_hash"] and got["_seq"] == 1


def test_append_only_rejects_duplicate():
    s = _store()
    s.append(_rec("q1"))
    try:
        s.append(_rec("q1"))
        assert False, "expected append-only violation"
    except ValueError:
        pass


def test_chain_valid():
    s = _store()
    for i in range(5):
        s.append(_rec(f"q{i}", answer=f"answer {i}"))
    res = s.verify_chain()
    assert res["valid"] is True and res["rows"] == 5


def test_tamper_detected():
    s = _store()
    for i in range(5):
        s.append(_rec(f"q{i}", answer=f"answer {i}"))
    forged = json.dumps({"query_id": "q2", "answer": "FORGED"}, sort_keys=True, separators=(",", ":"))
    with s._engine.begin() as conn:
        conn.execute(text("UPDATE audit SET payload = :p WHERE query_id = 'q2'"), {"p": forged})
    res = s.verify_chain()
    assert res["valid"] is False and res["broken_query_id"] == "q2"
