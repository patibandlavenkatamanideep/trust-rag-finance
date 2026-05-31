"""Chunk contract + a placeholder structure-aware chunker.

Deterministic chunk ids (D21): hash(document_id + version + section + index) so
re-ingestion upserts instead of duplicating. The real parser lands in Phase 2.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from pydantic import BaseModel

# Section headings common in financial filings. Used to split structure-aware.
_KNOWN_SECTIONS = [
    "Risk Factors",
    "Management's Discussion and Analysis",
    "Management Discussion",
    "Segment Information",
    "Business",
    "Financial Statements",
    "Notes to Financial Statements",
    "Quantitative and Qualitative Disclosures",
    "Legal Proceedings",
    "Controls and Procedures",
    "Properties",
    "Executive Compensation",
    "Liquidity and Capital Resources",
    "Results of Operations",
    "Outlook",
    "Services",
    "Products",
]
_DISCLOSURE_HINTS = ("forward-looking", "safe harbor", "disclaimer", "this presentation")


def _is_heading(line: str) -> Optional[str]:
    """Return a normalized section title if `line` looks like a heading, else None."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return None
    # Known-section match only when the phrase dominates the line (heading-like),
    # so "Services" matches a "Services" heading but NOT a sentence that merely
    # mentions services. The +12 slack allows prefixes like "Item 1A. ".
    for known in _KNOWN_SECTIONS:
        if known.lower() in stripped.lower() and len(stripped) <= len(known) + 12:
            return known
    # Heuristic: short ALL-CAPS or Title Case line with no terminal period.
    words = stripped.split()
    if 1 <= len(words) <= 8 and not stripped.endswith("."):
        if stripped.isupper() or stripped.istitle():
            return stripped.title()
    return None


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


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split a page's text into (section_title, section_text) by detected headings."""
    sections: list[tuple[str, list[str]]] = []
    current_title = "body"
    current_lines: list[str] = []
    for line in text.splitlines():
        heading = _is_heading(line)
        if heading:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = heading
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    return [(title, "\n".join(lines).strip()) for title, lines in sections if "".join(lines).strip()]


def chunk_loaded_document(
    *,
    document_id: str,
    pages: list[tuple[int, str]],
    version: str = "v1",
    target_tokens: int = 800,
    overlap_paragraphs: int = 1,
    **metadata,
) -> list[Chunk]:
    """Structure-aware, page-aware chunker for a loaded document.

    Walks each page, splits on detected section headings, then packs paragraphs
    into ~target_tokens chunks within a section (sections are never merged). Each
    chunk keeps its section title and the page it started on for citations.
    Disclosure-like sections are tagged in metadata.
    """
    chunks: list[Chunk] = []
    index = 0

    for page_no, page_text in pages:
        for section_title, section_text in _split_into_sections(page_text):
            is_disclosure = any(h in section_text.lower() for h in _DISCLOSURE_HINTS)
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section_text) if p.strip()]
            buf: list[str] = []
            approx = 0

            def flush(buf_local: list[str]) -> None:
                nonlocal index
                if not buf_local:
                    return
                body = "\n\n".join(buf_local)
                meta = dict(metadata)
                if is_disclosure:
                    meta["section_title"] = f"{section_title} [disclosure]"
                chunks.append(
                    Chunk(
                        chunk_id=make_chunk_id(document_id, version, f"{section_title}:{page_no}", index),
                        document_id=document_id,
                        section_title=meta.pop("section_title", section_title),
                        page=page_no,
                        text=body,
                        version=version,
                        **meta,
                    )
                )
                index += 1

            for para in paragraphs:
                approx += len(para.split())
                buf.append(para)
                if approx >= target_tokens:
                    flush(buf)
                    buf = buf[-overlap_paragraphs:] if overlap_paragraphs else []
                    approx = sum(len(p.split()) for p in buf)
            flush(buf)

    return chunks
