"""Ingestion: load -> metadata -> structure-aware chunk -> embed -> index.

Pure functions + an orchestration (`ingest_path`) that takes abstract seams
(ChunkStore, EmbeddingModel), so ingestion has no hard infrastructure dependency.
"""

from ingestion.chunk import Chunk, chunk_document, chunk_loaded_document
from ingestion.loaders import LoadedDocument, discover_documents, load_document
from ingestion.metadata import DocumentMetadata, extract_metadata
from ingestion.pipeline import (
    IngestResult,
    ingest_document,
    ingest_path,
    withdraw_document,
)

__all__ = [
    "Chunk",
    "chunk_document",
    "chunk_loaded_document",
    "LoadedDocument",
    "load_document",
    "discover_documents",
    "DocumentMetadata",
    "extract_metadata",
    "IngestResult",
    "ingest_document",
    "ingest_path",
    "withdraw_document",
]
