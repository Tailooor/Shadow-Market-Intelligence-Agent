from typing import Generator

import gradio as gr

from app.agents import RuntimeLLMConfig
from app.config import (
    DEFAULT_PROVIDER,
    PROVIDER_LABELS,
    PROVIDER_MODEL_CHOICES,
    ProviderId,
    default_model_for_provider,
    get_settings,
    provider_status_markdown,
    validate_provider_credentials,
)
from app.exporters import export_report_json, export_report_pdf
from app.pipeline import MarketIntelligenceService
from app.schemas import CompetitorReport, ToolToggles


def report_to_swot_rows(report: CompetitorReport) -> list[list[str]]:
    return [
        ["Estimated Pricing Tier", report.estimated_pricing_tier],
        ["Strengths", "; ".join(report.swot.strengths) or "N/A"],
        ["Weaknesses", "; ".join(report.swot.weaknesses) or "N/A"],
        ["Opportunities", "; ".join(report.swot.opportunities) or "N/A"],
        ["Threats", "; ".join(report.swot.threats) or "N/A"],
    ]


def report_to_markdown(report: CompetitorReport) -> str:
    swot_rows = "\n".join(
        [
            f"| Strengths | {'; '.join(report.swot.strengths) or 'N/A'} |",
            f"| Weaknesses | {'; '.join(report.swot.weaknesses) or 'N/A'} |",
            f"| Opportunities | {'; '.join(report.swot.opportunities) or 'N/A'} |",
            f"| Threats | {'; '.join(report.swot.threats) or 'N/A'} |",
        ]
    )

    source_rows = "\n".join(
        [f"- [{source.source_title}]({source.source_url}) [{source.category}, {source.confidence}]" for source in report.source_evidence]
    )

    top_leaving = "\n".join(
        [f"- {item}" for item in report.sentiment_drift_analysis.top_3_reasons_customers_are_leaving]
    )
    features = "\n".join([f"- {item}" for item in report.key_features])
    pain_points = "\n".join([f"- {item}" for item in report.customer_pain_points])
    stack = "\n".join([f"- {item}" for item in report.tech_stack_fingerprinting.inferred_stack])

    return f"""
# {report.company_name}

## Executive Summary
{report.executive_summary}

## Pricing Tier
**{report.estimated_pricing_tier}**

## Key Features
{features or "- No clear features extracted"}

## Customer Pain Points
{pain_points or "- No strong pain points extracted"}

## Recent Pivots
{report.recent_pivots}

## Sentiment Drift Analysis
{report.sentiment_drift_analysis.summary}

### Top 3 Reasons Customers Are Leaving
{top_leaving}

## Tech-Stack Fingerprinting
{report.tech_stack_fingerprinting.summary}

### Inferred Stack
{stack or "- No stack signals extracted"}

### Likely Product Direction
{report.tech_stack_fingerprinting.likely_product_direction}

## SWOT
| Category | Findings |
|---|---|
{swot_rows}

## Sources
{source_rows or "- No sources analyzed"}
""".strip()


def on_provider_change(provider: ProviderId) -> tuple[gr.Dropdown, str]:
    settings = get_settings()
    return (
        gr.Dropdown(
            choices=PROVIDER_MODEL_CHOICES[provider],
            value=default_model_for_provider(provider, settings),
            allow_custom_value=True,
        ),
        provider_status_markdown(provider, settings),
    )


def run_workflow(
    company_name: str,
    provider_name: ProviderId,
    model_name: str,
    enable_reddit_search: bool,
    enable_linkedin_analysis: bool,
    enable_reviews_analysis: bool,
) -> Generator[tuple[str, str, dict | None, list[list[str]] | None, str, str | None, str | None], None, None]:
    company_name = company_name.strip()
    model_name = model_name.strip()

    settings = get_settings()
    provider_message = provider_status_markdown(provider_name, settings)
    provider_issue = validate_provider_credentials(provider_name, settings)

    if not company_name:
        yield provider_message, "Enter a company name to begin.", None, None, "", None, None
        return

    if not model_name:
        yield provider_message, "Enter a model name before starting.", None, None, "", None, None
        return

    if provider_issue:
        yield provider_message, f"Cannot start run: {provider_issue}", None, None, "", None, None
        return

    trace_log: list[str] = []

    def trace(message: str) -> None:
        trace_log.append(message)

    toggles = ToolToggles(
        enable_reddit_search=enable_reddit_search,
        enable_linkedin_analysis=enable_linkedin_analysis,
        enable_reviews_analysis=enable_reviews_analysis,
    )

    runtime_config = RuntimeLLMConfig(provider=provider_name, model=model_name)
    service = MarketIntelligenceService(runtime_config)
    try:
        trace(
            f"Lead researcher started planning coverage for {company_name} "
            f"using {PROVIDER_LABELS[provider_name]} / {model_name}."
        )
        yield provider_message, "\n".join(trace_log), None, None, "", None, None

        plan = service.plan_research(company_name, toggles)
        trace(f"Lead researcher identified {len(plan.intel_gaps)} intel gaps and {len(plan.search_tasks)} search tasks.")
        yield provider_message, "\n".join(trace_log), None, None, "", None, None

        search_results = service.execute_searches(plan, toggles, trace)
        preview = {"urls": [result.model_dump() for result in search_results]}
        yield provider_message, "\n".join(trace_log), preview, None, "", None, None

        analyses = []
        for source in search_results:
            source_text = service.fetch_source_text(source, trace)
            if not source_text.strip():
                trace(f"Skipped source with no usable text: {source.url}")
                yield provider_message, "\n".join(trace_log), preview, None, "", None, None
                continue

            trace(f"Analyst agent is extracting signals from {source.title}.")
            analysis = service.analyze_source(company_name, plan, source, source_text)
            if analysis is not None:
                analyses.append(analysis)
                trace(f"Captured structured findings from {analysis.source_title} with {analysis.confidence} confidence.")
            else:
                trace(f"Analyst skipped {source.title} because the page content was empty.")
            yield provider_message, "\n".join(trace_log), preview, None, "", None, None

        trace(f"Synthesis agent is compiling the final SWOT and market narrative from {len(analyses)} analyzed sources.")
        yield provider_message, "\n".join(trace_log), preview, None, "", None, None

        report = service.synthesize_report(company_name, plan, analyses, trace_log)
        report_json_path = export_report_json(report)
        report_pdf_path = export_report_pdf(report)

        yield (
            provider_message,
            "\n".join(trace_log),
            report.model_dump(),
            report_to_swot_rows(report),
            report_to_markdown(report),
            report_json_path,
            report_pdf_path,
        )
    except Exception as exc:
        trace(f"Workflow failed: {exc}")
        yield provider_message, "\n".join(trace_log), None, None, "", None, None
    finally:
        service.close()


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="Shadow-Market Intelligence Agent",
    ) as demo:
        settings = get_settings()
        gr.Markdown(
            """
            <div class="hero">
              <h1>Shadow-Market Intelligence Agent</h1>
              <p>Multi-agent competitor research with Pydantic AI, OpenRouter, DuckDuckGo, and Gradio.</p>
            </div>
            """
        )

        with gr.Row():
            with gr.Column(scale=2):
                company_name = gr.Textbox(
                    label="Target Company",
                    placeholder="Acme SaaS",
                )
                provider_name = gr.Dropdown(
                    choices=[(label, key) for key, label in PROVIDER_LABELS.items()],
                    value=DEFAULT_PROVIDER,
                    label="LLM Provider",
                )
                model_name = gr.Dropdown(
                    choices=PROVIDER_MODEL_CHOICES[DEFAULT_PROVIDER],
                    value=default_model_for_provider(DEFAULT_PROVIDER, settings),
                    allow_custom_value=True,
                    label="Model",
                    info="Pick a suggested model or type your own provider-specific model ID.",
                )
            with gr.Column(scale=1):
                run_button = gr.Button("Run Intelligence Sweep", variant="primary")
                provider_status = gr.Markdown(
                    value=provider_status_markdown(DEFAULT_PROVIDER, settings),
                    label="Provider Status",
                )

        with gr.Row():
            enable_reddit = gr.Checkbox(label="Enable Reddit Search", value=True)
            enable_linkedin = gr.Checkbox(label="Enable LinkedIn Analysis", value=True)
            enable_reviews = gr.Checkbox(label="Enable Reviews Analysis", value=True)

        with gr.Row():
            thought_trace = gr.Textbox(label="Thought Trace", lines=16, buttons=["copy"])
            json_output = gr.JSON(label="Structured Report")

        swot_table = gr.Dataframe(
            headers=["Category", "Findings"],
            datatype=["str", "str"],
            label="Pricing + SWOT Snapshot",
            wrap=True,
        )

        report_markdown = gr.Markdown(label="Report")

        with gr.Row():
            json_file = gr.File(label="Download JSON")
            pdf_file = gr.File(label="Download PDF")

        run_button.click(
            fn=run_workflow,
            inputs=[company_name, provider_name, model_name, enable_reddit, enable_linkedin, enable_reviews],
            outputs=[provider_status, thought_trace, json_output, swot_table, report_markdown, json_file, pdf_file],
        )

        provider_name.change(
            fn=on_provider_change,
            inputs=[provider_name],
            outputs=[model_name, provider_status],
        )

    return demo
