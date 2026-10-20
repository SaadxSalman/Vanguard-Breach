"""LLM provider abstraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class LLMUnavailable(RuntimeError):
    """Raised when a provider cannot be reached — callers fall back to simulation."""


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    meta: dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    name = "base"
    deep_capable = True

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 max_tokens: int = 2048) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError
