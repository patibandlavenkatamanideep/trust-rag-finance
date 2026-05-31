import math

from shared.embeddings import StubEmbedder


def test_deterministic_and_normalized():
    e = StubEmbedder(dim=64)
    v1 = e.embed(["Apple services revenue grew"])[0]
    v2 = e.embed(["Apple services revenue grew"])[0]
    assert v1 == v2  # deterministic
    assert math.isclose(math.sqrt(sum(x * x for x in v1)), 1.0, abs_tol=1e-6)


def test_similar_text_more_similar_than_unrelated():
    e = StubEmbedder(dim=256)

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b))

    base = e.embed(["Apple services revenue grew across all segments"])[0]
    near = e.embed(["Apple services revenue grew this year"])[0]
    far = e.embed(["Tesla automotive gross margin declined"])[0]
    assert cos(base, near) > cos(base, far)
