from retrieval.fusion import reciprocal_rank_fusion


def test_rrf_rewards_agreement():
    bm25 = ["a", "b", "c"]
    dense = ["b", "a", "d"]
    fused = dict(reciprocal_rank_fusion([bm25, dense]))
    # 'b' is rank 2 then 1; 'a' is rank 1 then 2 — both appear twice and lead.
    assert set(list(dict(reciprocal_rank_fusion([bm25, dense])))[:2]) == {"a", "b"}
    assert fused["a"] > fused["c"]
    assert fused["b"] > fused["d"]


def test_rrf_single_list_preserves_order():
    fused = reciprocal_rank_fusion([["x", "y", "z"]])
    assert [doc for doc, _ in fused] == ["x", "y", "z"]


def test_rrf_empty():
    assert reciprocal_rank_fusion([]) == []
