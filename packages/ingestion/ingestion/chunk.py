"""Chunk contract + a placeholder structure-aware chunker.

Deterministic chunk ids (D21): hash(document_id + version + section + index) so
re-ingestion upserts instead of duplicating. The real parser lands in Phase 2.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    company: Optional[str] = None
    ticker: Optional[str] = None
    document_type: Optional[str] = None
    publish_date: Optional[str] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    text: str
    version: str = "v1"
    source_path: Optional[str] = None


def make_chunk_id(document_id: str, version: str, section_title: str, index: int) -> str:
    raw = f"{document_id}|{version}|{section_title}|{index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def chunk_document(
    *,
    document_id: str,
    text: str,
    section_title: str = "body",
    version: str = "v1",
    target_tokens: int = 800,
    **metadata,
) -> list[Chunk]:
    """Placeholder chunker: splits on blank lines, ~target_tokens per chunk.

    Phase 2 replaces this with section/heading/page-aware chunking that keeps
    tables intact and tags disclosures (D6).
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    buf: list[str] = []
    approx_tokens = 0
    idx = 0

    def flush() -> None:
        nonlocal buf, approx_tokens, idx
        if not buf:
            return
        body = "\n\n".join(buf)
        chunks.append(
            Chunk(
                chunk_id=make_chunk_id(document_id, version, section_title, idx),
                document_id=document_id,
                section_title=section_title,
                text=body,
                version=version,
                **metadata,
            )
        )
        idx += 1
        buf = []
        approx_tokens = 0

    for para in paragraphs:
        approx_tokens += len(para.split())
        buf.append(para)
        if approx_tokens >= target_tokens:
            flush()
    flush()
    return chunks
