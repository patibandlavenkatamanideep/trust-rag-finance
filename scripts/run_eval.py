"""Eval runner CLI — score the pipeline against the golden set, print + save.

    python scripts/run_eval.py            # extractive synthesizer (free, default)
    python scripts/run_eval.py --live     # use the configured LLM provider (costs)

Ingests data/sample_docs first if the index is empty. Writes the full result to
data/eval_results/latest.json for the dashboard (GET /eval/results).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for pkg in ("shared", "ingestion", "retrieval", "synthesis", "verification", "evals", "audit"):
    sys.path.insert(0, str(ROOT / "packages" / pkg))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from shared.config import get_settings  # noqa: E402
from shared.embeddings import get_embedder  # noqa: E402
from ingestion.pipeline import ingest_path  # noqa: E402
from retrieval.store import SqliteChunkStore  # noqa: E402
from evals.golden import load_golden  # noqa: E402
from evals.runner import run_eval  # noqa: E402

RESULTS_PATH = ROOT / "data" / "eval_results" / "latest.json"


def _ensure_corpus() -> None:
    cfg = get_settings()
    store = SqliteChunkStore(cfg.chunk_store_url)
    if store.count() == 0:
        print("Index empty — ingesting data/sample_docs ...")
        ingest_path(ROOT / "data" / "sample_docs", store, get_embedder(cfg))
    store.close()


def main(live: bool) -> None:
    _ensure_corpus()
    from app.deps import get_eval_pipeline, get_pipeline

    pipeline = get_pipeline() if live else get_eval_pipeline()
    mode = "LIVE LLM" if live else "extractive (no API)"
    golden = load_golden(ROOT / "data" / "golden_questions" / "golden.jsonl")
    print(f"Running {len(golden)} golden questions | synthesizer: {mode}\n")

    result = run_eval(pipeline, golden)
    m = result["metrics"]

    print("Metric                  value    bar     pass")
    print("-" * 48)
    from evals.metrics import DEPLOY_BARS

    for b in DEPLOY_BARS:
        val = m.get(b.name)
        if val is None:
            continue
        ok = result["gate"].get(b.name)
        print(f"  {b.name:<22} {val:<8} {b.direction}:{b.bar:<5} {'PASS' if ok else 'FAIL'}")
    print(f"  {'avg_latency_ms':<22} {m.get('avg_latency_ms')}")
    print(f"\nDEPLOY GATE: {'PASS' if result['deploy_ok'] else 'FAIL'}  "
          f"(n={m.get('n_questions')})")
    print(f"By category: {json.dumps(result['by_category'])}")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps({"mode": mode, **result}, indent=2), encoding="utf-8")
    print(f"\nSaved -> {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main(live="--live" in sys.argv[1:])
