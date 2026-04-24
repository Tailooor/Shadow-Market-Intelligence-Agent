from app.exporters import _slugify, _strip_markdown, export_report_json
from app.schemas import (
    CompetitorReport,
    SentimentDriftAnalysis,
    SourceAnalysis,
    SWOTAnalysis,
    TechStackFingerprint,
)


def test_slugify():
    assert _slugify("Acme SaaS!") == "acme-saas"
    assert _slugify("---") == "report"


def test_strip_markdown():
    assert _strip_markdown("**bold**") == "bold"
    assert _strip_markdown("`code`") == "code"
    assert _strip_markdown("[link](http://a.com)") == "link"
    assert _strip_markdown("## Heading") == "Heading"


def test_export_report_json(tmp_path, monkeypatch):
    monkeypatch.setattr("app.exporters.EXPORT_DIR", tmp_path)
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
        source_evidence=[
            SourceAnalysis(
                source_title="Example",
                source_url="http://example.com",
                category="general",
                summary="S",
                key_features=[],
                customer_pain_points=[],
                pricing_signals=[],
                tech_stack_signals=[],
                pivot_signals=[],
                churn_reasons=[],
                confidence="high",
            )
        ],
        trace=["started"],
    )
    path = export_report_json(report)
    assert path.endswith("acme-report.json")
    import json

    with open(path) as f:
        data = json.load(f)
    assert data["company_name"] == "Acme"
