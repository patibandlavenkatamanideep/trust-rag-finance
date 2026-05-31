"""Synthesis: grounded, schema-constrained cited generation, or abstain.

Two synthesizers behind one seam:
* ExtractiveSynthesizer — no LLM, relevance-gated, deterministic. Default; lets
  the system abstain correctly with zero API key.
* LLMSynthesizer — real model (Anthropic/OpenAI), used when a provider + key are
  configured. Both run the deterministic input guards (safety.py) first.
"""

from shared.config import Settings, get_settings

from synthesis.extractive import ExtractiveSynthesizer
from synthesis.llm import LLMSynthesizer
from synthesis.model import get_llm_client
from synthesis.safety import screen_input
from synthesis.stub import StubSynthesizer

__all__ = [
    "ExtractiveSynthesizer",
    "LLMSynthesizer",
    "StubSynthesizer",
    "screen_input",
    "get_synthesizer",
]


def get_synthesizer(settings: Settings | None = None):
    """Return the configured Synthesizer: LLM if wired, else extractive (no API)."""
    cfg = settings or get_settings()
    client = get_llm_client(cfg)
    if client is not None:
        return LLMSynthesizer(client)
    return ExtractiveSynthesizer()
