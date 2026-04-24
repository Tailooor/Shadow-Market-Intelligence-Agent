from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


PricingTier = Literal["Low", "Mid", "Enterprise", "Unknown"]
SourceCategory = Literal["pricing", "features", "reviews", "reddit", "linkedin", "news", "tech", "general"]
ConfidenceLevel = Literal["low", "medium", "high"]


class ToolToggles(BaseModel):
    enable_reddit_search: bool = True
    enable_linkedin_analysis: bool = True
    enable_reviews_analysis: bool = True


class IntelGap(BaseModel):
    name: str = Field(description="The missing intelligence area to investigate.")
    rationale: str = Field(description="Why this gap matters for competitive positioning.")
    priority: int = Field(ge=1, le=5, description="Priority from 1-5 where 5 is the highest.")


class SearchTask(BaseModel):
    query: str = Field(description="A search-engine-ready query.")
    purpose: str = Field(description="What this query should uncover.")
    category: SourceCategory = Field(description="The primary source category.")


class ResearchPlan(BaseModel):
    company_name: str
    intel_gaps: list[IntelGap] = Field(min_length=1)
    search_tasks: list[SearchTask] = Field(min_length=1)
    working_hypotheses: list[str] = Field(min_length=1)


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    query: str
    category: SourceCategory


class SourceAnalysis(BaseModel):
    source_title: str
    source_url: str
    category: SourceCategory
    summary: str
    key_features: list[str]
    customer_pain_points: list[str]
    pricing_signals: list[str]
    tech_stack_signals: list[str]
    pivot_signals: list[str]
    churn_reasons: list[str]
    confidence: ConfidenceLevel


class SentimentDriftAnalysis(BaseModel):
    summary: str
    top_3_reasons_customers_are_leaving: list[str] = Field(min_length=3, max_length=3)


class TechStackFingerprint(BaseModel):
    summary: str
    inferred_stack: list[str]
    hiring_signals: list[str]
    likely_product_direction: str


class SWOTAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]


class CompetitorReportDraft(BaseModel):
    company_name: str
    executive_summary: str
    estimated_pricing_tier: PricingTier
    key_features: list[str]
    customer_pain_points: list[str]
    recent_pivots: str = Field(description="Major changes, shifts, or directional clues from the last 6 months.")
    sentiment_drift_analysis: SentimentDriftAnalysis
    tech_stack_fingerprinting: TechStackFingerprint
    swot: SWOTAnalysis


class CompetitorReport(CompetitorReportDraft):
    source_evidence: list[SourceAnalysis]
    trace: list[str]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
