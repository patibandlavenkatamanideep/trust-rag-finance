"""Eval metric definitions + the asymmetric deploy gate (D8).

ALL bars hard-block deploy. The cardinal one is false-confident rate == 0:
a high-confidence wrong answer is the failure this whole system exists to kill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal


@dataclass(frozen=True)
class MetricBar:
    name: str
    description: str
    direction: Literal["min", "max", "exact"]
    bar: float

    def passes(self, value: float) -> bool:
        if self.direction == "min":
            return value >= self.bar
        if self.direction == "max":
            return value <= self.bar
        return value == self.bar


# The deploy gate. Tunable by advisors during the pilot, but all hard-block.
DEPLOY_BARS: list[MetricBar] = [
    MetricBar("groundedness", "every claim supported by cited span", "min", 0.98),
    MetricBar("false_confident_rate", "high-confidence AND wrong", "exact", 0.0),
    MetricBar("hallucination_rate", "any unsupported claim", "max", 0.02),
    MetricBar("citation_validity", "cited source exists in retrieved set", "exact", 1.0),
    MetricBar("recall_at_10", "correct report/section in top-k", "min", 0.90),
    MetricBar("correctness", "vs advisor-labeled expected", "min", 0.85),
    MetricBar("abstention_precision", "'not found' is actually correct", "min", 0.95),
]


def gate(results: dict[str, float]) -> dict[str, bool]:
    """Return per-metric pass/fail. Deploy only if every value is True."""
    out: dict[str, bool] = {}
    for m in DEPLOY_BARS:
        if m.name in results:
            out[m.name] = m.passes(results[m.name])
    return out
