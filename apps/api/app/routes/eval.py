"""Eval routes — stubbed in Phase 1, fully wired in Phase 7.

GET /eval/results returns the deploy bars + golden-set size so the dashboard has
something to render before the runner exists.
"""

from __future__ import annotations

from fastapi import APIRouter

from evals.golden import load_golden
from evals.metrics import DEPLOY_BARS

router = APIRouter(tags=["eval"], prefix="/eval")


@router.post("/run")
def run_eval() -> dict:
    # Phase 7 wires this to drive the live pipeline against the golden set.
    return {
        "status": "not_implemented",
        "detail": "Eval runner lands in Phase 7. Use scripts/run_eval.py once wired.",
    }


@router.get("/results")
def eval_results() -> dict:
    golden = load_golden()
    return {
        "golden_size": len(golden),
        "deploy_bars": [
            {"name": b.name, "direction": b.direction, "bar": b.bar} for b in DEPLOY_BARS
        ],
        "latest_run": None,
    }
