"""Document loaders. Turn a file on disk into page-aware raw text.

Supports .txt/.md natively and .pdf via pypdf (optional — install the 'ingest'
extra). Each loaded document is a list of (page_number, page_text) so the chunker
can keep page provenance for citations (D5/D6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".text"}


@dataclass
class LoadedDocument:
    document_id: str
    source_path: str
    pages: list[tuple[int, str]]  # (page_number, text), 1-indexed
    raw_metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(text for _, text in self.pages)


def load_document(path: str | Path) -> LoadedDocument:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"document not found: {p}")
    suffix = p.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return _load_text(p)
    if suffix == ".pdf":
        return _load_pdf(p)
    raise ValueError(f"unsupported file type '{suffix}' for {p.name}")


def _load_text(p: Path) -> LoadedDocument:
    text = p.read_text(encoding="utf-8", errors="replace")
    return LoadedDocument(document_id=p.stem, source_path=str(p), pages=[(1, text)])


def _load_pdf(p: Path) -> LoadedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "Reading PDFs requires the 'ingest' extra: pip install '.[ingest]'"
        ) from exc
    reader = PdfReader(str(p))
    pages = [(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]
    return LoadedDocument(document_id=p.stem, source_path=str(p), pages=pages)


def discover_documents(directory: str | Path) -> list[Path]:
    """Find all loadable documents under a directory (non-recursive + recursive)."""
    d = Path(directory)
    if not d.exists():
        return []
    suffixes = TEXT_SUFFIXES | {".pdf"}
    return sorted(
        f
        for f in d.rglob("*")
        if f.is_file()
        and f.suffix.lower() in suffixes
        and f.stem.lower() != "readme"  # skip guidance/readme files in corpus dirs
    )
