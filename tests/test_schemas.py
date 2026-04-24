import pytest
from pydantic import ValidationError

from app.schemas import (
    CompetitorReport,
    CompetitorReportDraft,
    IntelGap,
    ResearchPlan,
    SearchTask,
    SentimentDriftAnalysis,
    SourceAnalysis,
    SWOTAnalysis,
    TechStackFingerprint,
    ToolToggles,
)


def test_tool_toggles_defaults():
    t = ToolToggles()
    assert t.enable_reddit_search is True
    assert t.enable_linkedin_analysis is True
    assert t.enable_reviews_analysis is True


def test_intel_gap_priority_bounds():
    with pytest.raises(ValidationError):
        IntelGap(name="X", rationale="Y", priority=0)
    with pytest.raises(ValidationError):
        IntelGap(name="X", rationale="Y", priority=6)
    gap = IntelGap(name="X", rationale="Y", priority=3)
    assert gap.priority == 3


def test_research_plan_min_items():
    with pytest.raises(ValidationError):
        ResearchPlan(company_name="Acme", intel_gaps=[], search_tasks=[], working_hypotheses=[])


def test_search_task_category_validation():
    with pytest.raises(ValidationError):
        SearchTask(query="test", purpose="test", category="invalid")
    task = SearchTask(query="test", purpose="test", category="pricing")
    assert task.category == "pricing"


def test_competitor_report_draft_round_trip():
    draft = CompetitorReportDraft(
        company_name="Acme",
        executive_summary="Does things.",
        estimated_pricing_tier="Mid",
        key_features=["A", "B"],
        customer_pain_points=["C"],
        recent_pivots="None",
        sentiment_drift_analysis=SentimentDriftAnalysis(
            summary="Mixed",
            top_3_reasons_customers_are_leaving=["Price", "Bugs", "Support"],
        ),
        tech_stack_fingerprinting=TechStackFingerprint(
            summary="Cloud native",
            inferred_stack=["AWS", "React"],
            hiring_signals=["Rust"],
            likely_product_direction="AI features",
        ),
        swot=SWOTAnalysis(
            strengths=["Brand"],
            weaknesses=["Price"],
            opportunities=["AI"],
            threats=["Competition"],
        ),
    )
    dumped = draft.model_dump()
    assert dumped["company_name"] == "Acme"
    assert dumped["estimated_pricing_tier"] == "Mid"


def test_competitor_report_generated_at():
    report = CompetitorReport(
        company_name="Acme",
        executive_summary="Does things.",
        estimated_pricing_tier="Mid",
        key_features=["A"],
        customer_pain_points=["C"],
        recent_pivots="None",
        sentiment_drift_analysis=SentimentDriftAnalysis(
            summary="Mixed",
            top_3_reasons_customers_are_leaving=["Price", "Bugs", "Support"],
        ),
        tech_stack_fingerprinting=TechStackFingerprint(
            summary="Cloud native",
            inferred_stack=["AWS"],
            hiring_signals=["Rust"],
            likely_product_direction="AI features",
        ),
        swot=SWOTAnalysis(
            strengths=["Brand"],
            weaknesses=["Price"],
            opportunities=["AI"],
            threats=["Competition"],
        ),
        source_evidence=[],
        trace=["started"],
    )
    assert report.generated_at is not None
    assert report.generated_at.endswith("+00:00")


def test_source_analysis_confidence():
    with pytest.raises(ValidationError):
        SourceAnalysis(
            source_title="T",
            source_url="http://example.com",
            category="general",
            summary="S",
            key_features=[],
            customer_pain_points=[],
            pricing_signals=[],
            tech_stack_signals=[],
            pivot_signals=[],
            churn_reasons=[],
            confidence="invalid",
        )
