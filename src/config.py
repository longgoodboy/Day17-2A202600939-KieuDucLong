from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from model_provider import ProviderConfig, normalize_provider

@dataclass
class LabConfig:
    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig
    force_offline: bool

def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def load_config(base_dir: Path | None = None) -> LabConfig:
    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    data_dir = root / "data"
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    provider = normalize_provider(os.getenv("LLM_PROVIDER", "openai"))
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    judge_model_name = os.getenv("JUDGE_MODEL", model_name)
    compact_threshold_tokens = int(os.getenv("COMPACT_THRESHOLD_TOKENS", "300"))
    compact_keep_messages = int(os.getenv("COMPACT_KEEP_MESSAGES", "6"))
    force_offline = _env_bool("FORCE_OFFLINE", True)

    api_key = None if force_offline else os.getenv({
        "openai": "OPENAI_API_KEY",
        "custom": "CUSTOM_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "ollama": None,
        "openrouter": "OPENROUTER_API_KEY",
    }.get(provider, "OPENAI_API_KEY"))

    base_url = None
    if provider == "custom":
        base_url = os.getenv("CUSTOM_BASE_URL")
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL")
    elif provider == "openrouter":
        base_url = os.getenv("OPENROUTER_BASE_URL")

    model = ProviderConfig(provider=provider, model_name=model_name, temperature=0.0, api_key=api_key, base_url=base_url)
    judge_model = ProviderConfig(provider=provider, model_name=judge_model_name, temperature=0.0, api_key=api_key, base_url=base_url)
    return LabConfig(root, data_dir, state_dir, compact_threshold_tokens, compact_keep_messages, model, judge_model, force_offline)
