import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas import CompetitorReport


EXPORT_DIR = Path("exports")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "report"


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax so ReportLab doesn't render raw **text** or [links](url)."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.MULTILINE)
    return text.strip()


def export_report_json(report: CompetitorReport) -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"{_slugify(report.company_name)}-report.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return str(path.resolve())


def export_report_pdf(report: CompetitorReport) -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"{_slugify(report.company_name)}-report.pdf"

    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Shadow-Market Intelligence Report: {report.company_name}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(_strip_markdown(report.executive_summary), styles["BodyText"]),
        Spacer(1, 12),
        Paragraph(f"Estimated Pricing Tier: {report.estimated_pricing_tier}", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph("Key Features", styles["Heading2"]),
    ]

    for item in report.key_features:
        story.append(Paragraph(f"- {_strip_markdown(item)}", styles["BodyText"]))

    story.extend(
        [
            Spacer(1, 10),
            Paragraph("Customer Pain Points", styles["Heading2"]),
        ]
    )
    for item in report.customer_pain_points:
        story.append(Paragraph(f"- {_strip_markdown(item)}", styles["BodyText"]))

    story.extend(
        [
            Spacer(1, 10),
            Paragraph("Recent Pivots", styles["Heading2"]),
            Paragraph(_strip_markdown(report.recent_pivots), styles["BodyText"]),
            Spacer(1, 10),
            Paragraph("Sentiment Drift", styles["Heading2"]),
            Paragraph(_strip_markdown(report.sentiment_drift_analysis.summary), styles["BodyText"]),
        ]
    )
    for item in report.sentiment_drift_analysis.top_3_reasons_customers_are_leaving:
        story.append(Paragraph(f"- {_strip_markdown(item)}", styles["BodyText"]))

    story.extend(
        [
            Spacer(1, 10),
            Paragraph("Tech-Stack Fingerprinting", styles["Heading2"]),
            Paragraph(_strip_markdown(report.tech_stack_fingerprinting.summary), styles["BodyText"]),
        ]
    )
    for item in report.tech_stack_fingerprinting.inferred_stack:
        story.append(Paragraph(f"- {_strip_markdown(item)}", styles["BodyText"]))

    story.extend(
        [
            Spacer(1, 10),
            Paragraph("SWOT", styles["Heading2"]),
        ]
    )
    for label, items in {
        "Strengths": report.swot.strengths,
        "Weaknesses": report.swot.weaknesses,
        "Opportunities": report.swot.opportunities,
        "Threats": report.swot.threats,
    }.items():
        story.append(Paragraph(label, styles["Heading3"]))
        for item in items:
            story.append(Paragraph(f"- {_strip_markdown(item)}", styles["BodyText"]))

    story.extend(
        [
            Spacer(1, 10),
            Paragraph("Sources", styles["Heading2"]),
        ]
    )
    for source in report.source_evidence:
        story.append(Paragraph(f"- {source.source_title}: {source.source_url}", styles["BodyText"]))

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    doc.build(story)
    return str(path.resolve())
