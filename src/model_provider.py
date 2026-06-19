from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

@dataclass
class ProviderConfig:
    provider: str
    model_name: str
    temperature: float
    api_key: str | None = None
    base_url: str | None = None

def normalize_provider(value: str) -> str:
    aliases = {
        "anthorpic": "anthropic",
        "open-ai": "openai",
        "custom": "custom",
        "gemini": "gemini",
        "anthropic": "anthropic",
        "openai": "openai",
        "ollama": "ollama",
        "openrouter": "openrouter",
    }
    return aliases.get((value or "").strip().lower(), (value or "").strip().lower())

def build_chat_model(config: ProviderConfig):
    provider = normalize_provider(config.provider)
    if provider in {"openai", "custom"}:
        try:
            module = import_module("langchain_openai")
            ChatOpenAI = getattr(module, "ChatOpenAI")
        except Exception as exc:
            raise ImportError("langchain_openai is required for live OpenAI/custom providers") from exc
        kwargs = {"model": config.model_name, "temperature": config.temperature}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if provider == "custom" and config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenAI(**kwargs)
    if provider == "gemini":
        try:
            module = import_module("langchain_google_genai")
            ChatGoogleGenerativeAI = getattr(module, "ChatGoogleGenerativeAI")
        except Exception as exc:
            raise ImportError("langchain_google_genai is required for live gemini provider") from exc
        kwargs = {"model": config.model_name, "temperature": config.temperature}
        if config.api_key:
            kwargs["google_api_key"] = config.api_key
        return ChatGoogleGenerativeAI(**kwargs)
    if provider == "anthropic":
        try:
            module = import_module("langchain_anthropic")
            ChatAnthropic = getattr(module, "ChatAnthropic")
        except Exception as exc:
            raise ImportError("langchain_anthropic is required for live anthropic provider") from exc
        kwargs = {"model": config.model_name, "temperature": config.temperature}
        if config.api_key:
            kwargs["anthropic_api_key"] = config.api_key
        return ChatAnthropic(**kwargs)
    if provider == "ollama":
        try:
            module = import_module("langchain_ollama")
            ChatOllama = getattr(module, "ChatOllama")
        except Exception as exc:
            raise ImportError("langchain_ollama is required for live ollama provider") from exc
        kwargs = {"model": config.model_name, "temperature": config.temperature}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOllama(**kwargs)
    if provider == "openrouter":
        try:
            module = import_module("langchain_openrouter")
            ChatOpenRouter = getattr(module, "ChatOpenRouter")
        except Exception as exc:
            raise ImportError("langchain_openrouter is required for live openrouter provider") from exc
        kwargs = {"model_name": config.model_name, "temperature": config.temperature}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenRouter(**kwargs)
    raise ValueError(f"Unsupported provider: {config.provider}")
