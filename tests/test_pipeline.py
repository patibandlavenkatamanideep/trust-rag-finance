"""The skeleton must abstain when there is no evidence (safe default, S1)."""

from audit.memory import InMemoryAuditStore
from retrieval.stub import StubRetriever
from synthesis.stub import StubSynthesizer
from verification.citation import verify_citations
from verification.judge import StubJudge

from app.pipeline import QueryPipeline


class _Verifier:
    def verify(self, answer, sources):
        return verify_citations(answer, sources)


def _pipeline():
    return QueryPipeline(
        retriever=StubRetriever(),
        synthesizer=StubSynthesizer(),
        verifier=_Verifier(),
        judge=StubJudge(),
        audit=InMemoryAuditStore(),
    )


def test_no_sources_abstains():
    resp = _pipeline().run("What does Apple say about services revenue?")
    assert resp.abstained is True
    assert resp.confidence.band == "abstain"
    assert resp.answer == ""


def test_pipeline_writes_audit():
    pipe = _pipeline()
    resp = pipe.run("anything")
    record = pipe.audit.get(resp.query_id)
    assert record is not None
    assert record["user_query"] == "anything"
    assert record["confidence_band"] == "abstain"
