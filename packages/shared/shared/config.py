"""Centralized, env-driven configuration. No secrets in code (CLAUDE.md rule)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "TrustRAG Finance"
    environment: Literal["local", "dev", "pilot"] = "local"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://trustrag:trustrag@localhost:5432/trustrag",
        description="SQLAlchemy URL for Postgres (metadata, audit, eval results).",
    )

    # --- Model providers (keep provider-neutral; adapter selects impl) ---
    llm_provider: Literal["anthropic", "openai", "bedrock", "stub"] = "stub"
    embedding_provider: Literal["sentence_transformers", "openai", "voyage", "bedrock", "stub"] = "stub"
    reranker_provider: Literal["cross_encoder", "cohere", "stub"] = "stub"

    anthropic_api_key: str = ""
    openai_api_key: str = ""

    synthesis_model: str = "claude-sonnet-4-6"
    judge_model: str = "claude-opus-4-8"
    classify_model: str = "claude-haiku-4-5-20251001"

    # --- Embeddings / index store ---
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 256  # used by the deterministic stub embedder
    chunk_store_url: str = "sqlite:///data/index/chunks.db"

    # --- Retrieval ---
    retrieval_top_n: int = 50  # per-method candidate pool before fusion
    retrieval_top_k: int = 8  # after rerank, fed to synthesis
    rrf_k: int = 60  # RRF rank constant

    # --- Confidence thresholds (conservative to start, per D12) ---
    groundedness_floor: float = 0.98  # cardinal deploy-gate bar
    high_confidence_groundedness: float = 0.98


@lru_cache
def get_settings() -> Settings:
    return Settings()
