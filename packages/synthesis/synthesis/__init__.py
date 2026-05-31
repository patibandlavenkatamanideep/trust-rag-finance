"""Synthesis: grounded, schema-constrained cited generation.

Phase 1 ships a stub synthesizer that abstains (no sources -> no answer) and the
model-adapter seam. Phase 4 wires the real LLM behind the same `Synthesizer`
Protocol with the versioned prompt in `prompts.py`.
"""

from synthesis.stub import StubSynthesizer

__all__ = ["StubSynthesizer"]
