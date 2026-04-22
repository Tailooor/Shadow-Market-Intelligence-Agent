from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


ProviderId = Literal["openrouter", "google", "openai", "anthropic", "ollama"]

PROVIDER_LABELS: dict[ProviderId, str] = {
    "openrouter": "OpenRouter",
    "google": "Gemini",
    "openai": "OpenAI",
    "anthropic": "Claude",
    "ollama": "Ollama",
}

PROVIDER_MODEL_CHOICES: dict[ProviderId, list[str]] = {
    "openrouter": [
        "openrouter/free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
    ],
    "google": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ],
    "openai": [
        "gpt-5",
        "gpt-4.1",
        "gpt-4.1-mini",
    ],
    "anthropic": [
        "claude-sonnet-4-5",
        "claude-opus-4-1",
        "claude-3-5-haiku-latest",
    ],
    "ollama": [
        "llama3.2",
        "qwen2.5",
        "mistral",
    ],
}

DEFAULT_PROVIDER: ProviderId = "openrouter"


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    ollama_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    app_title: str = "Shadow-Market Intelligence Agent"
    app_url: str = "http://localhost:7860"
    http_timeout_seconds: int = 20
    max_search_results_per_task: int = 5
    max_sources_to_analyze: int = 6
    max_source_text_chars: int = 6000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def default_model_for_provider(provider: ProviderId, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    configured_defaults: dict[ProviderId, str] = {
        "openrouter": settings.openrouter_model,
        "google": settings.google_model,
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "ollama": settings.ollama_model,
    }
    return configured_defaults.get(provider) or PROVIDER_MODEL_CHOICES[provider][0]


def _is_blank(value: str | None) -> bool:
    return not value or not value.strip()


def validate_provider_credentials(provider: ProviderId, settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    if provider == "openrouter" and _is_blank(settings.openrouter_api_key):
        return "OPENROUTER_API_KEY is missing in `.env`."
    if provider == "google" and _is_blank(settings.google_api_key):
        return "GOOGLE_API_KEY is missing in `.env`."
    if provider == "openai" and _is_blank(settings.openai_api_key):
        return "OPENAI_API_KEY is missing in `.env`."
    if provider == "anthropic" and _is_blank(settings.anthropic_api_key):
        return "ANTHROPIC_API_KEY is missing in `.env`."
    if provider == "ollama" and _is_blank(settings.ollama_base_url):
        return "OLLAMA_BASE_URL is missing in `.env`."
    return None


def provider_status_markdown(provider: ProviderId, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    issue = validate_provider_credentials(provider, settings)
    label = PROVIDER_LABELS[provider]

    if issue:
        return f"**Provider:** {label}  \n**Status:** Missing configuration  \n**Action:** {issue}"

    if provider == "ollama":
        return (
            f"**Provider:** {label}  \n"
            f"**Status:** Ready  \n"
            f"**Base URL:** `{settings.ollama_base_url}`  \n"
            "Ollama usually works locally with just the base URL. `OLLAMA_API_KEY` is optional."
        )

    return f"**Provider:** {label}  \n**Status:** API key found in `.env`."
