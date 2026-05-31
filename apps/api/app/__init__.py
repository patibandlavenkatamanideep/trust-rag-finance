"""TrustRAG Finance API service (query-service).

Composition root: this is the only place concrete adapters are wired to the
abstract seams from `shared.interfaces`. Everything else depends on the
interfaces, not the implementations.

This package's import also bootstraps the monorepo path (below) so the service
runs with a plain `uvicorn app.main:app --app-dir apps/api` even without a
`pip install -e .`. When the package IS installed, these inserts are harmless
no-ops. Keeping it here means it runs before `app.main` imports `shared`, etc.
"""

import sys as _sys
from pathlib import Path as _Path

# repo root = .../<root>/apps/api/app/__init__.py -> parents[3]
_ROOT = _Path(__file__).resolve().parents[3]
for _pkg in (
    "packages/shared",
    "packages/ingestion",
    "packages/retrieval",
    "packages/synthesis",
    "packages/verification",
    "packages/evals",
    "packages/audit",
):
    _p = str(_ROOT / _pkg)
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
