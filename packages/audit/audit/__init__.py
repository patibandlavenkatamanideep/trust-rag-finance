"""Audit: append-only provenance trail (D24/D28).

MVP is a plain append-only table behind the `AuditStore` seam. The seam is
designed now so a WORM/SIEM/hash-chained adapter is a later swap, not a rewrite.
An in-memory adapter keeps the skeleton runnable without Postgres.
"""

from audit.memory import InMemoryAuditStore
from audit.models import AuditRecord

__all__ = ["InMemoryAuditStore", "AuditRecord"]
