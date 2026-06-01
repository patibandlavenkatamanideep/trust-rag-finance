"""The groundedness judge must independently catch ungrounded answers."""

from shared.schemas import Citation, CitedAnswer, Claim, Confidence, RetrievedSource
from verification.judge import EntailmentJudge, StubJudge


def _source(sid: str, text: str) -> RetrievedSource:
    return RetrievedSource(
        source_id=sid, chunk_id=f"c_{sid}", document_id="d",
        document_title="Apple 2024 Form 10-K", text=text,
    )


def _answer(claims, abstained=False) -> CitedAnswer:
    return CitedAnswer(
        answer="x", claims=claims, citations=[],
        confidence=Confidence(band="medium"), abstained=abstained,
    )


def test_grounded_answer_scores_high():
    src = [_source("source_1", "Apple services revenue grew across all geographic segments.")]
    ans = _answer([Claim(text="Apple services revenue grew across segments", source_ids=["source_1"], supported=True)])
    assert EntailmentJudge().score(ans, src) >= 0.8


def test_fabricated_claim_scores_low_even_if_flagged_supported():
    # Synthesizer LIES: marks supported=True, but the cited chunk doesn't support it.
    src = [_source("source_1", "Apple services revenue grew across all geographic segments.")]
    ans = _answer([Claim(text="Tesla automotive margins collapsed by forty percent", source_ids=["source_1"], supported=True)])
    score = EntailmentJudge().score(ans, src)
    assert score < 0.4  # independent re-check catches the unsupported claim


def test_abstain_scores_zero():
    assert EntailmentJudge().score(_answer([], abstained=True), []) == 0.0


def test_stub_judge_trusts_flags():
    # Contrast: the legacy stub would be fooled by the supported=True flag.
    src = [_source("source_1", "unrelated text")]
    ans = _answer([Claim(text="something false", source_ids=["source_1"], supported=True)])
    assert StubJudge().score(ans, src) == 1.0
    assert EntailmentJudge().score(ans, src) < 0.4
