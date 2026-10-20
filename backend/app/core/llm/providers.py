"""HTTP providers: OpenAI-compatible (OpenAI/DeepSeek/vLLM/Ollama) and Anthropic."""
from __future__ import annotations

import httpx

from ...config import get_settings
from .base import BaseProvider, LLMResponse, LLMUnavailable


class OpenAICompatibleProvider(BaseProvider):
    """Covers OpenAI, DeepSeek, vLLM-served models, Ollama, Groq, Together…"""

    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str, fast_model: str | None = None,
                 name: str = "openai") -> None:
        s = get_settings()
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.fast_model = fast_model or model
        self.timeout = s.llm_timeout
        self.retries = s.llm_retries

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 max_tokens: int = 2048, fast: bool = False) -> LLMResponse:
        model = self.fast_model if fast else self.model
        payload = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/chat/completions",
                                       headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"] or ""
                    return LLMResponse(text=text, provider=self.name, model=model,
                                       meta={"usage": data.get("usage", {})})
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
        raise LLMUnavailable(f"{self.name}: {last_error}")


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.anthropic_base_url.rstrip("/")
        self.api_key = s.anthropic_api_key
        self.model = s.anthropic_model
        self.timeout = s.llm_timeout
        self.retries = s.llm_retries

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 max_tokens: int = 2048, fast: bool = False) -> LLMResponse:
        payload = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature,
                   "system": system, "messages": [{"role": "user", "content": user}]}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    text = "".join(block.get("text", "") for block in data.get("content", []))
                    return LLMResponse(text=text, provider=self.name, model=self.model,
                                       meta={"usage": data.get("usage", {})})
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
        raise LLMUnavailable(f"anthropic: {last_error}")
