"""Hash-chained audit ledger: append-only + tamper-evident (D24)."""

import json

from audit.sqlite import SqliteAuditStore


def _rec(qid: str, answer: str = "a") -> dict:
    return {"query_id": qid, "user_query": "q", "answer": answer, "confidence_band": "high"}


def test_append_and_get():
    s = SqliteAuditStore("sqlite:///:memory:")
    s.append(_rec("q1"))
    got = s.get("q1")
    assert got["user_query"] == "q"
    assert got["_row_hash"] and got["_seq"] == 1


def test_append_only_rejects_duplicate():
    s = SqliteAuditStore("sqlite:///:memory:")
    s.append(_rec("q1"))
    try:
        s.append(_rec("q1"))
        assert False, "expected append-only violation"
    except ValueError:
        pass


def test_chain_valid_for_untampered_ledger():
    s = SqliteAuditStore("sqlite:///:memory:")
    for i in range(5):
        s.append(_rec(f"q{i}", answer=f"answer {i}"))
    result = s.verify_chain()
    assert result["valid"] is True
    assert result["rows"] == 5


def test_tampering_breaks_the_chain():
    s = SqliteAuditStore("sqlite:///:memory:")
    for i in range(5):
        s.append(_rec(f"q{i}", answer=f"answer {i}"))
    # Tamper: rewrite the payload of row 3 directly (simulating an attacker).
    forged = json.dumps({"query_id": "q2", "answer": "FORGED"}, sort_keys=True, separators=(",", ":"))
    s._conn.execute("UPDATE audit SET payload = ? WHERE query_id = 'q2'", (forged,))
    s._conn.commit()
    result = s.verify_chain()
    assert result["valid"] is False
    assert result["broken_query_id"] == "q2"
