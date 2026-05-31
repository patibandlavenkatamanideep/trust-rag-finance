"""Lightweight query parsing -> retrieval filters.

Extracts a ticker when the query clearly names one company (by ticker token or
company name), so retrieval can pre-filter. Conservative: returns a ticker only
on a confident single match; ambiguous/multi-company queries get no filter (a
wrong filter is worse than none — it could hide the right evidence).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Reuse the demo company map; keep in sync with ingestion.metadata.
_COMPANY_TO_TICKER = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "meta": "META",
    "jpmorgan": "JPM",
    "alphabet": "GOOGL",
    "google": "GOOGL",
}
_KNOWN_TICKERS = set(_COMPANY_TO_TICKER.values())
_TOKEN = re.compile(r"[A-Za-z]+")


@dataclass
class ParsedQuery:
    ticker: str | None = None


def parse_query(query: str) -> ParsedQuery:
    found: set[str] = set()

    # Explicit ticker tokens (uppercase in the original text).
    for tok in re.findall(r"\b[A-Z]{1,5}\b", query):
        if tok in _KNOWN_TICKERS:
            found.add(tok)

    # Company names (case-insensitive).
    lowered = query.lower()
    for name, ticker in _COMPANY_TO_TICKER.items():
        if re.search(rf"\b{name}\b", lowered):
            found.add(ticker)

    # Only filter on an unambiguous single company.
    return ParsedQuery(ticker=next(iter(found)) if len(found) == 1 else None)
