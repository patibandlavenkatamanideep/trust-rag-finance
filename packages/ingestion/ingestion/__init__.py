"""Ingestion: parse -> structure-aware chunk -> embed -> index.

Phase 1 ships the chunk contract and a stub loader. Phase 2 fills in real PDF
parsing, structure-aware chunking, embedding, and indexing.
"""

from ingestion.chunk import Chunk, chunk_document

__all__ = ["Chunk", "chunk_document"]
