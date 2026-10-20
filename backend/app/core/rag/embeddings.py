"""Embedding providers for the adversarial knowledge base.

Providers:
  local  – deterministic hashed unigram/bigram/char-ngram encoder (always available)
  openai – text-embedding-3-* via HTTP
  ollama – BGE-Large / nomic-embed-text served locally via Ollama
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any

import httpx

from ...config import get_settings

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _hash_bucket(token: str, dim: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % dim


class LocalHashEncoder:
    """Signed hashing trick over unigrams, bigrams and char 3-grams.

    Deterministic, dependency-free, and — importantly for adversarial work —
    reasonably robust to noise words and token splitting thanks to char-ngrams.
    """

    name = "local"

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or get_settings().local_embedding_dim

    def encode(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        words = _tokenize(text)
        feats: list[str] = list(words)
        feats += [f"{a}_{b}" for a, b in zip(words, words[1:])]
        compact = re.sub(r"\s+", " ", text.lower())
        feats += [compact[i:i + 3] for i in range(max(0, len(compact) - 2))]
        for feat in feats:
            bucket = _hash_bucket(feat, self.dim)
            sign = 1.0 if int(hashlib.blake2b(feat.encode(), digest_size=1).digest()[0]) % 2 else -1.0
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(t) for t in texts]


class OpenAIEmbedder:
    name = "openai"

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.openai_base_url.rstrip("/") + "/embeddings"
        self._key = s.openai_api_key
        self._model = s.openai_embedding_model

    def encode(self, text: str) -> list[float]:
        with httpx.Client(timeout=30) as client:
            resp = client.post(self._url, headers={"Authorization": f"Bearer {self._key}"},
                               json={"model": self._model, "input": text})
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=60) as client:
            resp = client.post(self._url, headers={"Authorization": f"Bearer {self._key}"},
                               json={"model": self._model, "input": texts})
            resp.raise_for_status()
            rows = sorted(resp.json()["data"], key=lambda r: r["index"])
            return [r["embedding"] for r in rows]


class OllamaEmbedder:
    name = "ollama"

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.ollama_base_url.rstrip("/") + "/api/embeddings"
        self._model = s.ollama_embedding_model

    def encode(self, text: str) -> list[float]:
        with httpx.Client(timeout=60) as client:
            resp = client.post(self._url, json={"model": self._model, "prompt": text})
            resp.raise_for_status()
            return resp.json()["embedding"]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(t) for t in texts]


def get_encoder(provider: str | None = None) -> Any:
    settings = get_settings()
    provider = (provider or settings.embedding_provider).lower()
    if provider == "openai":
        return OpenAIEmbedder()
    if provider == "ollama":
        return OllamaEmbedder()
    return LocalHashEncoder()
