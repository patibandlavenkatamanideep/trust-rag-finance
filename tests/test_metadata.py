from ingestion.metadata import extract_metadata


def test_extracts_ticker_type_year_from_filename():
    m = extract_metadata("data/sample_docs/AAPL_10-K_2024.txt")
    assert m.ticker == "AAPL"
    assert m.company == "Apple Inc."
    assert m.document_type == "10-K"
    assert m.publish_date == "2024"
    assert m.version == "v1"


def test_version_suffix_parsed():
    m = extract_metadata("NVDA_10-K_2024_v2.txt")
    assert m.ticker == "NVDA"
    assert m.version == "v2"


def test_unknown_fields_left_none_not_guessed():
    m = extract_metadata("random_notes.txt")
    assert m.document_type is None
    assert m.company is None
