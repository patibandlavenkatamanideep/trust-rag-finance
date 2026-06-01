"""Eval scoring: the kill metric (false-confident) must be computed correctly."""

from shared.schemas import (
    Confidence,
    GoldenQuestion,
    QueryResponse,
    RetrievedSource,
    VerificationResult,
)
from evals.metrics import aggregate_metrics, gate
from evals.runner import score_question


def _resp(*, abstained, band, groundedness, citation_validity, ticker=None):
    sources = (
        [RetrievedSource(source_id="source_1", chunk_id="c1", document_id="d",
                         document_title="t", ticker=ticker, text="x")]
        if ticker else []
    )
    return QueryResponse(
        query_id="q", answer="a", claims=[], citations=[],
        confidence=Confidence(band=band, groundedness_score=groundedness),
        verification=VerificationResult(citation_validity=citation_validity),
        retrieved_sources=sources, abstained=abstained,
    )


def _q(behavior, ticker="AAPL"):
    return GoldenQuestion(id="e", query="q", expected_behavior=behavior, ticker=ticker)


def test_correct_answer_not_false_confident():
    r = score_question(
        _q("answer"),
        _resp(abstained=False, band="high", groundedness=1.0, citation_validity=1.0, ticker="AAPL"),
        10,
    )
    assert r.correct and not r.false_confident and r.recall_hit


def test_high_confidence_on_abstain_question_is_false_confident():
    # System answered HIGH on a question that should have abstained -> cardinal failure.
    r = score_question(
        _q("abstain"),
        _resp(abstained=False, band="high", groundedness=1.0, citation_validity=1.0, ticker="AAPL"),
        10,
    )
    assert not r.correct and r.false_confident


def test_correct_abstention_is_correct_not_false_confident():
    r = score_question(
        _q("abstain"),
        _resp(abstained=True, band="abstain", groundedness=0.0, citation_validity=1.0),
        10,
    )
    assert r.correct and not r.false_confident


def test_aggregate_kill_metric_counts():
    records = [
        score_question(_q("answer"), _resp(abstained=False, band="high", groundedness=1.0, citation_validity=1.0, ticker="AAPL"), 5).__dict__,
        score_question(_q("abstain"), _resp(abstained=False, band="high", groundedness=1.0, citation_validity=1.0, ticker="AAPL"), 5).__dict__,
    ]
    m = aggregate_metrics(records)
    assert m["false_confident_rate"] == 0.5
    assert gate(m)["false_confident_rate"] is False  # bar is exactly 0
