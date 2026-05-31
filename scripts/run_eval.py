"""Eval runner entrypoint. Phase 1: loads the golden set and prints deploy bars.

Phase 7 drives the live pipeline against each golden question and computes the
seven metrics + the asymmetric deploy gate (D8).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for pkg in ("shared", "evals"):
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from evals.golden import load_golden  # noqa: E402
from evals.metrics import DEPLOY_BARS  # noqa: E402


def main() -> None:
    golden = load_golden(ROOT / "data" / "golden_questions" / "golden.jsonl")
    print(f"Loaded {len(golden)} golden question(s).")
    by_behavior: dict[str, int] = {}
    for q in golden:
        by_behavior[q.expected_behavior] = by_behavior.get(q.expected_behavior, 0) + 1
    print(f"  by expected behavior: {by_behavior}")
    print("\nDeploy gate (ALL hard-block):")
    for b in DEPLOY_BARS:
        print(f"  {b.name:<22} {b.direction:<5} {b.bar}  — {b.description}")
    print("\n(Phase 7 wires the runner that scores the live pipeline.)")


if __name__ == "__main__":
    main()
