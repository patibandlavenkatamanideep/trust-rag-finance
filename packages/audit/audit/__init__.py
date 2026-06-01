"""Audit: append-only provenance trail (D24/D28).

* SqliteAuditStore — durable, hash-chained, tamper-evident ledger (default).
* InMemoryAuditStore — process-local; used for tests and as a fallback.

Both implement the `AuditStore` seam, so a WORM/SIEM adapter is a later swap.
`get_audit_store(cfg)` selects by config.
"""

from audit.memory import InMemoryAuditStore
from audit.models import AuditRecord
from audit.sqlite import SqliteAuditStore

__all__ = ["InMemoryAuditStore", "SqliteAuditStore", "AuditRecord", "get_audit_store"]


def get_audit_store(settings=None):
    from shared.config import get_settings

    cfg = settings or get_settings()
    if cfg.audit_store == "memory":
        return InMemoryAuditStore()
    return SqliteAuditStore(cfg.audit_store_url)
