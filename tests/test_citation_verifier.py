"""Citation verification is a core differentiator — never ship it untested."""

from shared.schemas import Citation, CitedAnswer, Claim, Confidence, RetrievedSource
from verification.citation import verify_citations


def _source(source_id: str, text: str) -> RetrievedSource:
    return RetrievedSource(
        source_id=source_id,
        chunk_id=f"chunk_{source_id}",
        document_id="doc_1",
        document_title="Apple 2024 Form 10-K",
        text=text,
    )


def _answer(claims, citations, abstained=False) -> CitedAnswer:
    return CitedAnswer(
        answer="x",
        claims=claims,
        citations=citations,
        confidence=Confidence(band="medium"),
        abstained=abstained,
    )


def test_supported_claim_passes():
    sources = [_source("source_1", "Apple services revenue grew across all segments.")]
    ans = _answer(
        claims=[Claim(text="Apple services revenue grew", source_ids=["source_1"], supported=True)],
        citations=[Citation(source_id="source_1", document_title="Apple 2024 Form 10-K")],
    )
    res = verify_citations(ans, sources)
    assert res.citation_validity == 1.0
    assert res.all_claims_supported is True
    assert res.unsupported_claims == []


def test_citation_outside_retrieval_set_is_invalid():
    sources = [_source("source_1", "Apple services revenue grew.")]
    ans = _answer(
        claims=[Claim(text="Apple services revenue grew", source_ids=["source_99"])],
        citations=[Citation(source_id="source_99", document_title="Ghost Report")],
    )
    res = verify_citations(ans, sources)
    assert "source_99" in res.invalid_citations
    assert res.all_claims_supported is False


def test_claim_without_lexical_support_is_unsupported():
    sources = [_source("source_1", "Apple services revenue grew across all segments.")]
    ans = _answer(
        claims=[Claim(text="Tesla automotive margins declined sharply", source_ids=["source_1"])],
        citations=[Citation(source_id="source_1", document_title="Apple 2024 Form 10-K")],
    )
    res = verify_citations(ans, sources)
    assert res.unsupported_claims  # no overlap -> flagged


def test_claim_with_no_source_is_unsupported():
    sources = [_source("source_1", "Apple services revenue grew.")]
    ans = _answer(claims=[Claim(text="Apple services revenue grew", source_ids=[])], citations=[])
    res = verify_citations(ans, sources)
    assert "Apple services revenue grew" in res.unsupported_claims


def test_abstain_is_valid_with_no_claims():
    res = verify_citations(_answer(claims=[], citations=[], abstained=True), [])
    assert res.all_claims_supported is True
