"""Ingestion entrypoint (Phase 2 fills in real parsing/embedding/indexing).

Phase 1: demonstrates the chunk contract by chunking a text file and printing
the deterministic chunk ids. Run: python scripts/ingest.py data/sample_docs/<file>.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the monorepo packages importable when run directly.
ROOT = Path(__file__).resolve().parents[1]
for pkg in ("shared", "ingestion"):
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from ingestion.chunk import chunk_document  # noqa: E402


def main(path: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    chunks = chunk_document(
        document_id=p.stem,
        text=text,
        section_title="body",
        source_path=str(p),
    )
    print(f"Chunked {p.name} into {len(chunks)} chunk(s):")
    for c in chunks:
        print(f"  {c.chunk_id}  ({len(c.text.split())} words)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/ingest.py <path-to-text-file>")
        raise SystemExit(1)
    main(sys.argv[1])
