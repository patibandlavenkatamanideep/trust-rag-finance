"""Ingestion orchestration: load -> metadata -> chunk -> embed -> store.

A pure-ish DAG: it receives a ChunkStore and an EmbeddingModel (both abstract
seams) so it has no hard infra dependency. Idempotent via deterministic chunk
ids; version-aware via supersede (old version's chunks flip to 'superseded'
before the new version's chunks are written as 'current').
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from shared.interfaces import ChunkStore, EmbeddingModel
from shared.logging import get_logger

from ingestion.chunk import chunk_loaded_document
from ingestion.loaders import discover_documents, load_document
from ingestion.metadata import extract_metadata

log = get_logger("ingestion")

_VERSION_SUFFIX = re.compile(r"_v\d+$", re.IGNORECASE)


@dataclass
class IngestResult:
    document_id: str
    version: str
    chunks_written: int
    superseded: int


def _logical_document_id(stem: str) -> str:
    """Strip a trailing _vN so versions of the same report share an identity."""
    return _VERSION_SUFFIX.sub("", stem)


def ingest_document(
    path: str | Path, store: ChunkStore, embedder: EmbeddingModel, target_tokens: int = 800
) -> IngestResult:
    loaded = load_document(path)
    meta = extract_metadata(loaded.source_path, loaded.full_text[:1000])
    logical_id = _logical_document_id(loaded.document_id)

    chunks = chunk_loaded_document(
        document_id=logical_id,
        pages=loaded.pages,
        version=meta.version,
        target_tokens=target_tokens,
        company=meta.company,
        ticker=meta.ticker,
        document_type=meta.document_type,
        publish_date=meta.publish_date,
        document_title=meta.document_title,
        source_path=loaded.source_path,
    )
    if not chunks:
        log.info("no chunks produced", extra={"fields": {"document_id": logical_id}})
        return IngestResult(logical_id, meta.version, 0, 0)

    embeddings = embedder.embed([c.text for c in chunks])

    # Supersede any prior version's chunks for this logical document, then write.
    superseded = store.set_status(logical_id, "superseded")

    records = []
    for chunk, emb in zip(chunks, embeddings):
        records.append(
            {
                "chunk_id": chunk.chunk_id,
                "document_id": logical_id,
                "document_title": meta.document_title,
                "company": chunk.company,
                "ticker": chunk.ticker,
                "document_type": chunk.document_type,
                "publish_date": chunk.publish_date,
                "section_title": chunk.section_title,
                "page": chunk.page,
                "text": chunk.text,
                "version": chunk.version,
                "source_path": chunk.source_path,
                "status": "current",
                "embedding": emb,
            }
        )
    written = store.upsert(records)
    log.info(
        "ingested document",
        extra={"fields": {"document_id": logical_id, "version": meta.version,
                          "chunks": written, "superseded": superseded}},
    )
    return IngestResult(logical_id, meta.version, written, superseded)


def ingest_path(
    path: str | Path, store: ChunkStore, embedder: EmbeddingModel
) -> list[IngestResult]:
    """Ingest a single file or every supported document under a directory."""
    p = Path(path)
    targets = [p] if p.is_file() else discover_documents(p)
    return [ingest_document(t, store, embedder) for t in targets]


def withdraw_document(document_id: str, store: ChunkStore) -> int:
    """Compliance-critical: flip a document's chunks to 'withdrawn' (excluded)."""
    return store.set_status(document_id, "withdrawn")
