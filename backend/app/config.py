"""Vanguard-Breach configuration.

Loads the single master ``.env`` at the repository root and exposes a typed,
cached settings object used across the platform. Nothing else in the codebase
reads environment variables directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# backend/app/config.py -> parents[0]=app, [1]=backend, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def _load_env_file(path: Path) -> dict[str, str]:
    """Minimal, dependency-free .env parser (KEY=VALUE, # comments, quotes)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


_ENV_PATH = Path(os.environ.get("VANGUARD_ENV_FILE", DEFAULT_ENV_FILE))
_FILE_VALUES = _load_env_file(_ENV_PATH)

def env(key: str, default: str = "") -> str:
    """Environment lookup with file fallback: real env wins over .env file."""
    value = os.environ.get(key)
    if value is not None and value != "":
        return value
    return _FILE_VALUES.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(env(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_float(key: str, default: float) -> float:
    try:
        return float(env(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: str = "") -> list[str]:
    return [p.strip() for p in env(key, default).split(",") if p.strip()]


@dataclass(frozen=True)
class Settings:
    # core
    env_name: str = env("VANGUARD_ENV", "development")
    host: str = env("VANGUARD_HOST", "127.0.0.1")
    port: int = env_int("VANGUARD_PORT", 8000)
    log_level: str = env("VANGUARD_LOG_LEVEL", "INFO")
    data_dir: Path = REPO_ROOT / env("VANGUARD_DATA_DIR", "data")
    db_path: Path = REPO_ROOT / env("VANGUARD_DB_PATH", "data/vanguard.db")
    cors_origins: list[str] = field(default_factory=lambda: env_list(
        "VANGUARD_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
    auth_enabled: bool = env_bool("VANGUARD_AUTH_ENABLED", False)
    api_key: str = env("VANGUARD_API_KEY", "vb-console-key")

    # llm
    llm_provider: str = env("VANGUARD_LLM_PROVIDER", "simulation")
    llm_temperature: float = env_float("VANGUARD_LLM_TEMPERATURE", 0.7)
    llm_timeout: int = env_int("VANGUARD_LLM_TIMEOUT_SECONDS", 60)
    llm_retries: int = env_int("VANGUARD_LLM_MAX_RETRIES", 2)
    llm_max_tokens: int = env_int("VANGUARD_LLM_MAX_TOKENS", 2048)

    openai_api_key: str = env("OPENAI_API_KEY", "")
    openai_base_url: str = env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = env("OPENAI_MODEL", "gpt-4o-mini")
    openai_deep_model: str = env("OPENAI_DEEP_MODEL", "gpt-4o")
    openai_embedding_model: str = env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    anthropic_api_key: str = env("ANTHROPIC_API_KEY", "")
    anthropic_base_url: str = env("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    anthropic_model: str = env("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    deepseek_api_key: str = env("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = env("DEEPSEEK_MODEL", "deepseek-r1")
    deepseek_fast_model: str = env("DEEPSEEK_FAST_MODEL", "deepseek-chat")

    vllm_base_url: str = env("VLLM_BASE_URL", "http://localhost:8001/v1")
    vllm_api_key: str = env("VLLM_API_KEY", "vllm-local-no-auth")
    vllm_model: str = env("VLLM_MODEL", "meta-llama/Meta-Llama-3-70B-Instruct")
    vllm_fast_model: str = env("VLLM_FAST_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Llama-70B")

    ollama_base_url: str = env("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_embedding_model: str = env("OLLAMA_EMBEDDING_MODEL", "bge-large")

    # embeddings / vector store
    embedding_provider: str = env("VANGUARD_EMBEDDING_PROVIDER", "local")
    local_embedding_dim: int = env_int("VANGUARD_LOCAL_EMBEDDING_DIM", 384)
    vector_store: str = env("VANGUARD_VECTOR_STORE", "local")
    qdrant_url: str = env("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str = env("QDRANT_API_KEY", "")
    qdrant_collection: str = env("QDRANT_COLLECTION", "vanguard_threats")
    milvus_uri: str = env("MILVUS_URI", "http://localhost:19530")
    milvus_token: str = env("MILVUS_TOKEN", "")
    milvus_collection: str = env("MILVUS_COLLECTION", "vanguard_threats")

    # campaign engine
    max_chain_depth: int = env_int("VANGUARD_MAX_CHAIN_DEPTH", 4)
    max_iterations: int = env_int("VANGUARD_MAX_ITERATIONS", 12)
    severity_threshold: float = env_float("VANGUARD_SEVERITY_THRESHOLD", 6.0)
    default_seed: int = env_int("VANGUARD_DEFAULT_SEED", 1337)
    max_payloads_per_technique: int = env_int("VANGUARD_MAX_PAYLOADS_PER_TECHNIQUE", 3)

    # sandbox
    sandbox_mode: str = env("VANGUARD_SANDBOX_MODE", "inprocess")
    target_base_url: str = env("VANGUARD_TARGET_BASE_URL", "http://localhost:8100")
    target_superuser_token: str = env("TARGET_SUPERUSER_TOKEN", "sbx-root")
    target_internal_api_key: str = env("TARGET_INTERNAL_API_KEY", "sk-sandbox-internal")
    target_db_write_token: str = env("TARGET_DB_WRITE_TOKEN", "dbw")
    target_support_bot_token: str = env("TARGET_SUPPORT_BOT_TOKEN", "support")
    canary_tenant_a: str = env("CANARY_TENANT_A", "CANARY-TKA-000")
    canary_tenant_b: str = env("CANARY_TENANT_B", "CANARY-TKB-000")

    # reporting
    report_dir: Path = REPO_ROOT / env("VANGUARD_REPORT_DIR", "data/reports")
    report_author: str = env("VANGUARD_REPORT_AUTHOR", "Vanguard-Breach")
    company_name: str = env("VANGUARD_COMPANY_NAME", "Example Enterprise")

    @property
    def env_file_path(self) -> Path:
        return _ENV_PATH

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.report_dir, self.db_path.parent):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings


def env(key: str, default: str = "") -> str:
    """Environment lookup with file fallback: real env wins over .env file."""
    value = os.environ.get(key)
    if value is not None and value != "":
        return value
    return _FILE_VALUES.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(env(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_float(key: str, default: float) -> float:
    try:
        return float(env(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: str = "") -> list[str]:
    return [p.strip() for p in env(key, default).split(",") if p.strip()]
