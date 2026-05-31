"""Ingestion entrypoint: load -> chunk -> embed -> store into the ChunkStore.

Usage:
    python scripts/ingest.py data/sample_docs/AAPL_10-K_2024.txt
    python scripts/ingest.py data/sample_docs            # whole directory

Composition root: wires the concrete SqliteChunkStore + the configured embedder
to the ingestion orchestration (which depends only on the seams).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the monorepo packages importable when run directly (no install needed).
ROOT = Path(__file__).resolve().parents[1]
for pkg in ("shared", "ingestion", "retrieval"):
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from shared.config import get_settings  # noqa: E402
from shared.embeddings import get_embedder  # noqa: E402
from shared.logging import configure_logging  # noqa: E402
from ingestion.pipeline import ingest_path  # noqa: E402
from retrieval.store import SqliteChunkStore  # noqa: E402


def main(target: str) -> None:
    cfg = get_settings()
    configure_logging(cfg.log_level)

    store = SqliteChunkStore(cfg.chunk_store_url)
    embedder = get_embedder(cfg)

    results = ingest_path(target, store, embedder)
    if not results:
        print(f"No supported documents found at: {target}")
        return

    total = 0
    for r in results:
        total += r.chunks_written
        print(
            f"  {r.document_id} (v={r.version}): {r.chunks_written} chunk(s)"
            f"{f', superseded {r.superseded}' if r.superseded else ''}"
        )
    print(f"\nIngested {total} chunk(s) across {len(results)} document(s).")
    print(f"Store now holds {store.count()} chunk(s) at {cfg.chunk_store_url}")
    store.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/ingest.py <file-or-directory>")
        raise SystemExit(1)
    main(sys.argv[1])
