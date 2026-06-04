"""Fetch real public 10-K filings from SEC EDGAR into data/sample_docs/.

Public-domain filings, free API, no key. SEC requires a descriptive User-Agent
with contact info and rate-limits to ~10 req/s; this script sets a UA (override
with SEC_USER_AGENT) and sleeps between calls.

Usage:
    python scripts/fetch_edgar.py AAPL NVDA MSFT
    SEC_USER_AGENT="Your Name your@email.com" python scripts/fetch_edgar.py AAPL

Writes data/sample_docs/<TICKER>_10-K_<YEAR>.txt with the key narrative sections
(Item 1A Risk Factors, Item 7 MD&A, Item 1 Business) so the existing ingestion
pipeline picks up ticker/type/year from the filename and chunks by section.

This is best-effort HTML->text extraction for a demo corpus, not a filing parser.
"""

from __future__ import annotations

import html
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "research_reports"  # the live, self-updating corpus
USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "TrustRAG Finance (educational project) contact@example.com"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

# Item markers used to slice the narrative sections out of the plain text.
_SECTION_BOUNDS = [
    ("Business", r"item\s*1\.?\s*business", r"item\s*1a"),
    ("Risk Factors", r"item\s*1a\.?\s*risk\s*factors", r"item\s*1b"),
    ("Management's Discussion and Analysis", r"item\s*7\.?\s*management", r"item\s*7a"),
]


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(0.2)  # be polite to SEC
    return resp


def _ticker_to_cik() -> dict[str, int]:
    data = _get(TICKERS_URL).json()
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def _latest_10k(cik: int) -> tuple[str, str, str] | None:
    """Return (accession_no_nodashes, primary_document, filing_date) for newest 10-K."""
    data = _get(SUBMISSIONS_URL.format(cik=cik)).json()
    recent = data["filings"]["recent"]
    for form, acc, doc, date in zip(
        recent["form"], recent["accessionNumber"], recent["primaryDocument"], recent["filingDate"]
    ):
        if form == "10-K":
            return acc.replace("-", ""), doc, date
    return None


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
    return raw.strip()


def _extract_sections(text: str) -> str:
    low = text.lower()
    out: list[str] = []
    for title, start_pat, end_pat in _SECTION_BOUNDS:
        starts = [m.start() for m in re.finditer(start_pat, low)]
        ends = [m.start() for m in re.finditer(end_pat, low)]
        if not starts:
            continue
        start = starts[-1]  # the body occurrence, not the TOC entry
        end = next((e for e in ends if e > start), min(start + 60000, len(text)))
        body = text[start:end].strip()
        if len(body) > 400:
            out.append(f"{title}\n\n{body}")
    return "\n\n".join(out)


def fetch_ticker(ticker: str, cik_map: dict[str, int]) -> Path | None:
    ticker = ticker.upper()
    cik = cik_map.get(ticker)
    if cik is None:
        print(f"  {ticker}: not found in EDGAR ticker map")
        return None
    latest = _latest_10k(cik)
    if latest is None:
        print(f"  {ticker}: no 10-K found")
        return None
    acc, doc, date = latest
    url = ARCHIVE_URL.format(cik=cik, acc=acc, doc=doc)
    text = _html_to_text(_get(url).text)
    sections = _extract_sections(text) or text[:200000]
    year = date.split("-")[0]
    out = OUT_DIR / f"{ticker}_10-K_{year}.txt"
    header = f"{ticker} Form 10-K ({date}) — source: {url}\n\n"
    out.write_text(header + sections, encoding="utf-8")
    print(f"  {ticker}: wrote {out.name} ({len(sections):,} chars from {date} filing)")
    return out


def main(tickers: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Using SEC User-Agent: {USER_AGENT}")
    if "example.com" in USER_AGENT:
        print("  (set SEC_USER_AGENT='Your Name your@email.com' to identify yourself to SEC)")
    cik_map = _ticker_to_cik()
    for t in tickers:
        try:
            fetch_ticker(t, cik_map)
        except requests.HTTPError as exc:
            print(f"  {t}: HTTP error {exc}")
        except Exception as exc:  # noqa: BLE001 - report, don't hide
            print(f"  {t}: failed ({exc})")
    print("\nNow ingest: python scripts/ingest.py data/sample_docs")


if __name__ == "__main__":
    args = sys.argv[1:] or ["AAPL", "NVDA", "MSFT"]
    main(args)
