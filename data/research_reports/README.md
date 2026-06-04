# Live research corpus

This is the **live corpus** scanned by ingestion and the nightly job (Phase 9).
Drop real public equity-research documents here (`.txt` or `.pdf`), named with the
metadata convention `TICKER_DOCTYPE_YEAR[_vN].ext`, e.g. `AAPL_10-K_2024.txt`.

- New/updated files are picked up idempotently (deterministic chunk ids); a new
  version supersedes the old one automatically.
- Pull real SEC filings with `python scripts/fetch_edgar.py AAPL NVDA MSFT`.
- The `/ingest/webhook` endpoint also writes published reports here.

When this folder is empty, the system falls back to `data/sample_docs/` so the
demo still works. Keep 15–25 real reports here for the "always live" target.
PDFs are gitignored; commit small `.txt` extracts for a reproducible corpus.
