from ingestion.chunk import chunk_loaded_document


def test_section_and_page_provenance():
    page_text = (
        "Risk Factors\n\n"
        "The Company faces supply constraints and customer concentration risk.\n\n"
        "Results of Operations\n\n"
        "Data Center revenue grew substantially this year.\n"
    )
    chunks = chunk_loaded_document(
        document_id="NVDA_10-K_2024", pages=[(1, page_text)], version="v1", target_tokens=50
    )
    sections = {c.section_title for c in chunks}
    assert "Risk Factors" in sections
    assert "Results Of Operations" in sections or "Results of Operations" in sections
    assert all(c.page == 1 for c in chunks)
    assert all(c.document_id == "NVDA_10-K_2024" for c in chunks)


def test_chunk_ids_deterministic_across_runs():
    pages = [(1, "Business\n\nNVIDIA is a full-stack computing company.")]
    a = chunk_loaded_document(document_id="d", pages=pages)
    b = chunk_loaded_document(document_id="d", pages=pages)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
