"""Provider-neutral LLM adapter seam. Keep one interface; swap providers freely.

No provider is hardcoded into the pipeline. Adapters are lazy (import + client
created only when selected) so the project runs with zero LLM deps until you set
a provider + key. Anthropic is the default target (latest Claude models).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from shared.config import Settings


@runtime_checkable
class LLMClient(Protocol):
    """Minimal text-in/text-out contract the synthesizer needs."""

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str: ...


class AnthropicClient:
    """Adapter for the Anthropic Messages API (lazy import)."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError("LLM_PROVIDER=anthropic requires: pip install '.[llm]'") from exc
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")


class OpenAIClient:
    """Adapter for the OpenAI Chat Completions API (lazy import)."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError("LLM_PROVIDER=openai requires: pip install '.[llm]'") from exc
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


class GeminiClient:
    """Adapter for Google Gemini via the REST API (no SDK dependency).

    Uses generateContent with JSON response mode, which suits the CitedAnswer
    schema the synthesizer expects.
    """

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._api_key = api_key
        self._model = model or "gemini-2.5-flash"

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        import requests

        url = self.URL.format(model=self._model)
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.0,
                "responseMimeType": "application/json",
                # Gemini 2.5 'flash' is a thinking model; thinking tokens count
                # against maxOutputTokens. Disable it so the budget goes to JSON.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        resp = requests.post(
            url, json=body, headers={"x-goog-api-key": self._api_key}, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise ValueError(f"Gemini returned no candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise ValueError(
                f"Gemini returned no text (finishReason="
                f"{candidates[0].get('finishReason')})"
            )
        return text


def _model_name(settings: Settings) -> str:
    return settings.llm_model or settings.synthesis_model


def get_llm_client(settings: Settings) -> LLMClient | None:
    """Return a configured LLM client, or None when no provider is wired (stub)."""
    if settings.llm_provider == "anthropic":
        return AnthropicClient(settings.anthropic_api_key, _model_name(settings))
    if settings.llm_provider == "openai":
        return OpenAIClient(settings.openai_api_key, _model_name(settings))
    if settings.llm_provider == "gemini":
        return GeminiClient(settings.gemini_api_key, settings.llm_model or "gemini-2.5-flash")
    # 'bedrock' adapter is a later addition; 'stub' => no client.
    return None
