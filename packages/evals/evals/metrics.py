"""Eval metric definitions + the asymmetric deploy gate (D8).

ALL bars hard-block deploy. The cardinal one is false-confident rate == 0:
a high-confidence wrong answer is the failure this whole system exists to kill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


def aggregate_metrics(per_question: list[dict]) -> dict[str, float]:
    """Aggregate per-question eval records into the 7 deploy metrics + latency.

    Each record (produced by evals.runner) carries the booleans/values:
      expected_abstain, abstained, band, correct, recall_hit, citation_valid,
      groundedness, false_confident, latency_ms, is_answer_q.
    """
    n = len(per_question)
    if n == 0:
        return {}

    answer_qs = [r for r in per_question if r["is_answer_q"]]
    abstained_qs = [r for r in per_question if r["abstained"]]

    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    # Groundedness + citation validity measured on answered (non-abstained) questions.
    answered = [r for r in per_question if not r["abstained"]]
    groundedness = _mean([r["groundedness"] for r in answered])
    citation_validity = (
        1.0 if all(r["citation_valid"] for r in answered) else
        _mean([1.0 if r["citation_valid"] else 0.0 for r in answered])
    )
    recall = _mean([1.0 if r["recall_hit"] else 0.0 for r in answer_qs])
    correctness = _mean([1.0 if r["correct"] else 0.0 for r in per_question])
    abstention_precision = _mean(
        [1.0 if r["expected_abstain"] else 0.0 for r in abstained_qs]
    ) if abstained_qs else 1.0
    false_confident_rate = round(
        sum(1 for r in per_question if r["false_confident"]) / n, 4
    )
    hallucination_rate = round(
        sum(1 for r in answered if not r["citation_valid"]) / max(len(answered), 1), 4
    )

    return {
        "groundedness": groundedness,
        "false_confident_rate": false_confident_rate,
        "hallucination_rate": hallucination_rate,
        "citation_validity": citation_validity,
        "recall_at_10": recall,
        "correctness": correctness,
        "abstention_precision": abstention_precision,
        "avg_latency_ms": _mean([r["latency_ms"] for r in per_question]),
        "n_questions": n,
    }
