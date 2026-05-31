"""Evals: golden dataset + metrics + runner. Eval is first-class, not last.

Phase 1 ships the golden loader and the metric definitions (with the asymmetric
deploy bars, D8). The full runner that drives the live pipeline lands in Phase 7.
"""

from evals.golden import load_golden
from evals.metrics import DEPLOY_BARS, MetricBar

__all__ = ["load_golden", "DEPLOY_BARS", "MetricBar"]
