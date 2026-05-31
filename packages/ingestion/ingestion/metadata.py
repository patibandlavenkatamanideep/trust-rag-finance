"""Document-level metadata extraction.

Heuristics from the filename first (cheap, deterministic), with light content
fallbacks. Convention: `TICKER_DOCTYPE_YEAR[_vN].ext`, e.g.
`AAPL_10-K_2024.txt`, `NVDA_10-K_2024_v2.txt`. Unknown fields are left None
rather than guessed — abstaining from a guess beats a wrong label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Small demo ticker->company map. Extend as the corpus grows; unknown = None.
_TICKER_COMPANY = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "TSLA": "Tesla, Inc.",
    "META": "Meta Platforms, Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "GOOGL": "Alphabet Inc.",
}

_DOCTYPES = ["10-K", "10-Q", "8-K", "ARS", "TRANSCRIPT", "PRESENTATION", "RESEARCH"]
_TICKER_RE = re.compile(r"^[A-Z]{1,5}$")
_YEAR_RE = re.compile(r"(19|20)\d{2}")
_VERSION_RE = re.compile(r"_v(\d+)$", re.IGNORECASE)


@dataclass
class DocumentMetadata:
    ticker: Optional[str] = None
    company: Optional[str] = None
    document_type: Optional[str] = None
    publish_date: Optional[str] = None  # ISO date or year string
    version: str = "v1"
    document_title: str = ""


def extract_metadata(source_path: str | Path, sample_text: str = "") -> DocumentMetadata:
    p = Path(source_path)
    stem = p.stem

    version = "v1"
    vm = _VERSION_RE.search(stem)
    if vm:
        version = f"v{int(vm.group(1))}"
        stem = _VERSION_RE.sub("", stem)

    parts = re.split(r"[_\-\s]+", stem)
    ticker = next((part.upper() for part in parts if _TICKER_RE.match(part.upper())
                   and part.upper() in _TICKER_COMPANY), None)
    if ticker is None:
        # fall back to any 1-5 letter all-caps token
        ticker = next((part.upper() for part in parts if _TICKER_RE.match(part.upper())), None)

    doc_type = next(
        (dt for dt in _DOCTYPES if dt.replace("-", "").lower() in stem.replace("-", "").lower()),
        None,
    )

    year_match = _YEAR_RE.search(stem) or _YEAR_RE.search(sample_text[:500])
    publish_date = year_match.group(0) if year_match else None

    company = _TICKER_COMPANY.get(ticker or "", None)

    title_bits = [b for b in (company or ticker, publish_date, doc_type) if b]
    document_title = " ".join(str(b) for b in title_bits) or p.stem

    return DocumentMetadata(
        ticker=ticker,
        company=company,
        document_type=doc_type,
        publish_date=publish_date,
        version=version,
        document_title=document_title,
    )
