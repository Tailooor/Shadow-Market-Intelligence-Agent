import pytest

from app.pipeline import MarketIntelligenceService
from app.schemas import SearchResult, ToolToggles


@pytest.fixture
def service():
    config = type("obj", (object,), {"provider": "openrouter", "model": "openrouter/free"})()
    svc = MarketIntelligenceService(config)
    yield svc
    import asyncio

    asyncio.run(svc.close())


def test_fallback_tasks_all_enabled(service):
    toggles = ToolToggles(
        enable_reddit_search=True,
        enable_linkedin_analysis=True,
        enable_reviews_analysis=True,
    )
    tasks = service._fallback_tasks("Acme", toggles)
    categories = {t.category for t in tasks}
    assert categories == {"pricing", "features", "tech", "reviews", "reddit", "linkedin"}


def test_fallback_tasks_all_disabled(service):
    toggles = ToolToggles(
        enable_reddit_search=False,
        enable_linkedin_analysis=False,
        enable_reviews_analysis=False,
    )
    tasks = service._fallback_tasks("Acme", toggles)
    categories = {t.category for t in tasks}
    assert categories == {"pricing", "features", "tech"}


def test_fetch_source_text_empty_on_error(service):
    import asyncio

    trace_log = []

    def trace(msg):
        trace_log.append(msg)

    result = asyncio.run(
        service.fetch_source_text(
            SearchResult(title="Bad", url="http://localhost:99999/nope", snippet="", query="", category="general"),
            trace,
        )
    )
    assert result == ""
    assert any("Fetch failed" in m for m in trace_log)
