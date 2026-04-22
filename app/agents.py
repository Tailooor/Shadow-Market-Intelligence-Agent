from dataclasses import dataclass

from pydantic_ai import Agent

from app.config import get_settings
from app.schemas import CompetitorReportDraft, ResearchPlan, SourceAnalysis


LEAD_RESEARCHER_INSTRUCTIONS = """
You are the Lead Researcher for a shadow-market intelligence workflow.

Your job:
1. Identify the most important missing intelligence gaps about the target company.
2. Produce search-engine-ready search tasks that help uncover pricing, product, reviews, community chatter, job postings, and technology direction.
3. Favor evidence that helps a freelancer or consultant advise a client on market positioning.

Rules:
- Be practical and specific.
- Prioritize high-signal searches over generic ones.
- Include targeted searches for pricing, customer pain, and technical hiring clues.
- Use category values from the provided schema only.
- Do not invent facts about the company. Only create a research plan.
""".strip()


ANALYST_INSTRUCTIONS = """
You are the Analyst Agent in a competitor-intelligence pipeline.

You will receive one source page at a time. Extract only what can be reasonably supported by the source.

Focus on:
- key features
- pricing clues
- tech-stack clues
- customer pain points
- churn or dissatisfaction reasons
- recent pivots or directional signals

Rules:
- Prefer concrete signals over vague summaries.
- If the source is weak, say so through lower confidence and sparse fields.
- Do not hallucinate missing data.
""".strip()


SYNTHESIS_INSTRUCTIONS = """
You are the final synthesis agent for a competitor intelligence report.

You will receive:
- a research plan
- structured source analyses
- the original company name

Produce a concise but business-useful report for sales, strategy, or freelance consulting work.

Requirements:
- Estimate the pricing tier as Low, Mid, Enterprise, or Unknown.
- Summarize the top customer pain points.
- Write a sentiment drift analysis with exactly 3 reasons customers are leaving.
- Infer likely technology direction from job posts, site clues, and tool mentions.
- Output a formal SWOT analysis.
- Use only the evidence provided in the structured analyses.
- If evidence is weak, say so clearly instead of overclaiming.
""".strip()


@dataclass(frozen=True)
class RuntimeLLMConfig:
    provider: str
    model: str


def _build_model(runtime_config: RuntimeLLMConfig):
    settings = get_settings()
    provider_name = runtime_config.provider
    model_name = runtime_config.model

    if provider_name == "openrouter":
        from pydantic_ai.models.openrouter import OpenRouterModel
        from pydantic_ai.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            app_title=settings.app_title,
            app_url=settings.app_url,
        )
        return OpenRouterModel(model_name, provider=provider)

    if provider_name == "google":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        provider = GoogleProvider(api_key=settings.google_api_key)
        return GoogleModel(model_name, provider=provider)

    if provider_name == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key=settings.openai_api_key)
        return OpenAIChatModel(model_name, provider=provider)

    if provider_name == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        return AnthropicModel(model_name, provider=provider)

    if provider_name == "ollama":
        from pydantic_ai.models.ollama import OllamaModel
        from pydantic_ai.providers.ollama import OllamaProvider

        provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key or None,
        )
        return OllamaModel(model_name, provider=provider)

    raise ValueError(f"Unsupported provider: {provider_name}")


def build_lead_researcher(runtime_config: RuntimeLLMConfig) -> Agent[None, ResearchPlan]:
    return Agent(
        _build_model(runtime_config),
        instructions=LEAD_RESEARCHER_INSTRUCTIONS,
        output_type=ResearchPlan,
    )


def build_analyst(runtime_config: RuntimeLLMConfig) -> Agent[None, SourceAnalysis]:
    return Agent(
        _build_model(runtime_config),
        instructions=ANALYST_INSTRUCTIONS,
        output_type=SourceAnalysis,
    )


def build_synthesis_agent(runtime_config: RuntimeLLMConfig) -> Agent[None, CompetitorReportDraft]:
    return Agent(
        _build_model(runtime_config),
        instructions=SYNTHESIS_INSTRUCTIONS,
        output_type=CompetitorReportDraft,
    )
