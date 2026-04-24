from app.config import (
    PROVIDER_LABELS,
    default_model_for_provider,
    get_settings,
    validate_provider_credentials,
)


def test_provider_labels_coverage():
    assert set(PROVIDER_LABELS.keys()) == {"openrouter", "google", "openai", "anthropic", "ollama"}


def test_validate_openrouter_missing_key():
    class FakeSettings:
        openrouter_api_key = ""
        google_api_key = "x"
        openai_api_key = "x"
        anthropic_api_key = "x"
        ollama_base_url = "http://localhost:11434/v1"

    result = validate_provider_credentials("openrouter", FakeSettings())
    assert result is not None
    assert "OPENROUTER_API_KEY" in result


def test_validate_ollama_missing_base_url():
    class FakeSettings:
        openrouter_api_key = "x"
        google_api_key = "x"
        openai_api_key = "x"
        anthropic_api_key = "x"
        ollama_base_url = ""

    result = validate_provider_credentials("ollama", FakeSettings())
    assert result is not None
    assert "OLLAMA_BASE_URL" in result


def test_default_model_for_provider():
    settings = get_settings()
    model = default_model_for_provider("openrouter", settings)
    assert model == settings.openrouter_model
