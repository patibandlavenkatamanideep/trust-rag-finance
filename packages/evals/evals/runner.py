"""Eval runner — drive the live pipeline over the golden set and score it.

Produces a per-question record and the aggregated 7 deploy metrics. The scoring
operationalizes the asymmetric bar (S1): the kill metric is false-confident rate
(high confidence AND wrong), so abstaining when you should answer is "incorrect"
but NOT false-confident, while answering high-confidence when you should abstain
IS false-confident.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from shared.schemas import GoldenQuestion, QueryResponse

from evals.metrics import aggregate_metrics, gate


@dataclass
class QuestionResult:
    id: str
    query: str
    category: str
    expected_behavior: str
    is_answer_q: bool
    expected_abstain: bool
    abstained: bool
    band: str
    recall_hit: bool
    citation_valid: bool
    groundedness: float
    correct: bool
    false_confident: bool
    latency_ms: int


def _recall_hit(q: GoldenQuestion, resp: QueryResponse) -> bool:
    """Did retrieval surface the expected company's document in the top-k?"""
    if not q.ticker:
        return False
    tickers = {(s.ticker or "").upper() for s in resp.retrieved_sources}
    return q.ticker.upper() in tickers


def score_question(q: GoldenQuestion, resp: QueryResponse, latency_ms: int) -> QuestionResult:
    is_answer_q = q.expected_behavior == "answer"
    expected_abstain = q.expected_behavior == "abstain"
    abstained = resp.abstained
    band = resp.confidence.band
    citation_valid = resp.verification.citation_validity >= 1.0
    recall_hit = _recall_hit(q, resp)

    if expected_abstain:
        correct = abstained
    else:
        # Correct answer: didn't abstain, retrieved the right company, grounded, cited.
        correct = (not abstained) and recall_hit and citation_valid and (
            resp.confidence.groundedness_score > 0.0
        )

    # False-confident = system asserted HIGH confidence but was wrong. The cardinal failure.
    false_confident = (band == "high") and (not correct)

    return QuestionResult(
        id=q.id,
        query=q.query,
        category=q.category,
        expected_behavior=q.expected_behavior,
        is_answer_q=is_answer_q,
        expected_abstain=expected_abstain,
        abstained=abstained,
        band=band,
        recall_hit=recall_hit,
        citation_valid=citation_valid,
        groundedness=resp.confidence.groundedness_score,
        correct=correct,
        false_confident=false_confident,
        latency_ms=latency_ms,
    )


def run_eval(pipeline, golden: list[GoldenQuestion]) -> dict[str, Any]:
    """Run every golden question through `pipeline` and aggregate metrics."""
    results: list[QuestionResult] = []
    for q in golden:
        t0 = time.perf_counter()
        resp = pipeline.run(q.query)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        results.append(score_question(q, resp, latency_ms))

    records = [asdict(r) for r in results]
    metrics = aggregate_metrics(records)
    gate_result = gate(metrics)

    # Slice metrics by category (portfolio dashboards love this).
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        c = by_category.setdefault(r.category, {"n": 0, "correct": 0, "false_confident": 0})
        c["n"] += 1
        c["correct"] += int(r.correct)
        c["false_confident"] += int(r.false_confident)

    return {
        "metrics": metrics,
        "gate": gate_result,
        "deploy_ok": all(gate_result.values()) if gate_result else False,
        "by_category": by_category,
        "questions": records,
    }
