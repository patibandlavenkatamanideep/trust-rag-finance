from ingestion.chunk import chunk_document, make_chunk_id


def test_chunk_ids_are_deterministic():
    a = make_chunk_id("doc_1", "v1", "body", 0)
    b = make_chunk_id("doc_1", "v1", "body", 0)
    assert a == b
    assert a != make_chunk_id("doc_1", "v1", "body", 1)


def test_chunk_document_produces_chunks():
    text = "\n\n".join(f"paragraph {i} " + "word " * 200 for i in range(3))
    chunks = chunk_document(document_id="doc_1", text=text, target_tokens=150)
    assert len(chunks) >= 2
    assert all(c.document_id == "doc_1" for c in chunks)
    assert all(c.chunk_id for c in chunks)
