"""Eval routes — run the golden-set eval and serve dashboard results.

POST /eval/run drives the pipeline over the golden set and returns the 7 deploy
metrics + gate. Defaults to the no-API extractive synthesizer (?live=true uses
the configured LLM provider). GET /eval/results returns the last saved run.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from evals.golden import load_golden
from evals.metrics import DEPLOY_BARS
from evals.runner import run_eval

from app.deps import get_eval_pipeline, get_pipeline

router = APIRouter(tags=["eval"], prefix="/eval")

_RESULTS_PATH = Path("data/eval_results/latest.json")


@router.post("/run")
def run(live: bool = Query(False, description="Use the configured LLM provider (costs).")) -> dict:
    golden = load_golden()
    if not golden:
        return {"status": "no_golden_set", "detail": "data/golden_questions/golden.jsonl is empty"}
    pipeline = get_pipeline() if live else get_eval_pipeline()
    result = run_eval(pipeline, golden)
    result["mode"] = "LIVE LLM" if live else "extractive (no API)"
    _RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _RESULTS_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"status": "ok", "deploy_ok": result["deploy_ok"], "metrics": result["metrics"]}


@router.get("/results")
def results() -> dict:
    golden = load_golden()
    bars = [{"name": b.name, "direction": b.direction, "bar": b.bar} for b in DEPLOY_BARS]
    if _RESULTS_PATH.exists():
        latest = json.loads(_RESULTS_PATH.read_text(encoding="utf-8"))
        return {"golden_size": len(golden), "deploy_bars": bars, "latest_run": latest}
    return {"golden_size": len(golden), "deploy_bars": bars, "latest_run": None}
