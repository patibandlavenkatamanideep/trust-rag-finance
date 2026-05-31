"""Deterministic input guards — run before synthesis, no LLM required.

These catch the categories that must ALWAYS abstain regardless of retrieval:
personalized investment advice, prompt-injection attempts, and obviously
out-of-scope requests. Deterministic = auditable + reproducible (a regulator can
read the rule). The LLM, when added, is an additional layer, not a replacement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# --- Personalized investment advice (the system never advises an end client) --
_ADVICE_PATTERNS = [
    r"\bshould i\b",
    r"\bmy client\b",
    r"\bmy portfolio\b",
    r"\b(buy|sell|short)\b.*\b(for me|my client|right now|now)\b",
    r"\b(tell|advise|recommend)\b.*\b(my client|me to)\b",
    r"\bwhat should (i|we|my client)\b",
    r"\bis it a (good )?(buy|sell)\b",
    r"\b(allocate|invest)\b.*\bmy\b",
]

# --- Prompt-injection / instruction-override attempts -------------------------
_INJECTION_PATTERNS = [
    r"ignore (all |the )?(previous|prior|above) instructions",
    r"disregard (all |the )?(previous|prior|above)",
    r"forget (all |everything|your) (previous|instructions|rules)",
    r"you are now\b",
    r"\bsystem prompt\b",
    r"\bact as\b.*\b(unrestricted|jailbroken|dan)\b",
    r"\boverride\b.*\b(rules|instructions|safety)\b",
    r"reveal (your )?(system )?prompt",
]

_ADVICE_RE = [re.compile(p, re.IGNORECASE) for p in _ADVICE_PATTERNS]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


@dataclass
class InputScreen:
    blocked: bool
    reason: Optional[str] = None  # machine code: advice | injection
    message: Optional[str] = None  # human-facing abstain message


def screen_input(query: str) -> InputScreen:
    """Return a blocking screen result, or a non-blocking pass."""
    for rx in _INJECTION_RE:
        if rx.search(query):
            return InputScreen(
                blocked=True,
                reason="prompt_injection",
                message="This request looks like an attempt to override the assistant's "
                "instructions. The assistant only answers grounded research questions.",
            )
    for rx in _ADVICE_RE:
        if rx.search(query):
            return InputScreen(
                blocked=True,
                reason="personalized_advice",
                message="This assistant is read-only research support and does not provide "
                "personalized investment advice or buy/sell recommendations.",
            )
    return InputScreen(blocked=False)
