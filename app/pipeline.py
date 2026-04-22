from collections import OrderedDict
from typing import Callable

import httpx
import trafilatura
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from app.agents import RuntimeLLMConfig, build_analyst, build_lead_researcher, build_synthesis_agent
from app.config import get_settings
from app.schemas import CompetitorReport, ResearchPlan, SearchResult, SearchTask, SourceAnalysis, ToolToggles


TraceFn = Callable[[str], None]


class MarketIntelligenceService:
    def __init__(self, runtime_config: RuntimeLLMConfig) -> None:
        self.settings = get_settings()
        self.runtime_config = runtime_config
        self.lead_researcher = build_lead_researcher(runtime_config)
        self.analyst = build_analyst(runtime_config)
        self.synthesis_agent = build_synthesis_agent(runtime_config)
        self.http = httpx.Client(
            timeout=self.settings.http_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
                )
            },
        )

    def close(self) -> None:
        self.http.close()

    def plan_research(self, company_name: str, toggles: ToolToggles) -> ResearchPlan:
        prompt = f"""
Target company: {company_name}

Tool toggles:
- Reddit search enabled: {toggles.enable_reddit_search}
- LinkedIn analysis enabled: {toggles.enable_linkedin_analysis}
- Reviews analysis enabled: {toggles.enable_reviews_analysis}

Create a high-value research plan for a competitor intelligence workflow.
""".strip()
        result = self.lead_researcher.run_sync(prompt)
        return result.output

    def execute_searches(self, plan: ResearchPlan, toggles: ToolToggles, trace: TraceFn) -> list[SearchResult]:
        filtered_tasks = []
        for task in plan.search_tasks:
            if task.category == "reddit" and not toggles.enable_reddit_search:
                continue
            if task.category == "linkedin" and not toggles.enable_linkedin_analysis:
                continue
            if task.category == "reviews" and not toggles.enable_reviews_analysis:
                continue
            filtered_tasks.append(task)

        if not filtered_tasks:
            filtered_tasks = self._fallback_tasks(plan.company_name, toggles)

        trace(f"Search specialist queued {len(filtered_tasks)} targeted searches.")
        deduped: OrderedDict[str, SearchResult] = OrderedDict()

        for task in filtered_tasks:
            trace(f"Searching for {task.category} evidence: {task.query}")
            try:
                with DDGS() as ddgs:
                    results = ddgs.text(task.query, max_results=self.settings.max_search_results_per_task)
                    for item in results:
                        url = item.get("href") or item.get("url")
                        title = item.get("title") or url or "Untitled result"
                        if not url or url in deduped:
                            continue
                        deduped[url] = SearchResult(
                            title=title,
                            url=url,
                            snippet=item.get("body", ""),
                            query=task.query,
                            category=task.category,
                        )
            except Exception as exc:
                trace(f"Search failed for query '{task.query}': {exc}")

        ranked = list(deduped.values())[: self.settings.max_sources_to_analyze]
        trace(f"Collected {len(ranked)} unique URLs for source analysis.")
        return ranked

    def fetch_source_text(self, source: SearchResult, trace: TraceFn) -> str:
        trace(f"Fetching source: {source.url}")
        try:
            response = self.http.get(source.url)
            response.raise_for_status()
            html = response.text
        except Exception as exc:
            trace(f"Fetch failed for {source.url}: {exc}")
            return ""

        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_links=False,
            include_images=False,
            favor_precision=True,
        )
        text = extracted or BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        return text[: self.settings.max_source_text_chars]

    def analyze_source(self, company_name: str, plan: ResearchPlan, source: SearchResult, source_text: str) -> SourceAnalysis | None:
        if not source_text.strip():
            return None

        prompt = f"""
Target company: {company_name}
Source category: {source.category}
Source title: {source.title}
Source URL: {source.url}
Search query that found it: {source.query}
Snippet: {source.snippet}

Research plan context:
{plan.model_dump_json(indent=2)}

Source text:
{source_text}
""".strip()

        result = self.analyst.run_sync(prompt)
        analysis = result.output
        return analysis.model_copy(
            update={
                "source_title": analysis.source_title or source.title,
                "source_url": analysis.source_url or source.url,
                "category": analysis.category or source.category,
            }
        )

    def synthesize_report(
        self,
        company_name: str,
        plan: ResearchPlan,
        analyses: list[SourceAnalysis],
        trace_log: list[str],
    ) -> CompetitorReport:
        prompt = f"""
Target company: {company_name}

Research plan:
{plan.model_dump_json(indent=2)}

Structured source analyses:
{[analysis.model_dump() for analysis in analyses]}
""".strip()
        result = self.synthesis_agent.run_sync(prompt)
        draft = result.output
        return CompetitorReport(
            **draft.model_dump(),
            source_evidence=analyses,
            trace=trace_log,
        )

    def _fallback_tasks(self, company_name: str, toggles: ToolToggles) -> list[SearchTask]:
        tasks = [
            SearchTask(query=f"{company_name} pricing", purpose="Find pricing evidence.", category="pricing"),
            SearchTask(query=f"{company_name} features", purpose="Find feature evidence.", category="features"),
            SearchTask(query=f"{company_name} tech stack", purpose="Find technology clues.", category="tech"),
        ]
        if toggles.enable_reviews_analysis:
            tasks.append(SearchTask(
                query=f'site:trustpilot.com "{company_name}" reviews',
                purpose="Find review sentiment.",
                category="reviews",
            ))
        if toggles.enable_reddit_search:
            tasks.append(SearchTask(
                query=f'site:reddit.com "{company_name}" review OR complaints',
                purpose="Find Reddit customer chatter.",
                category="reddit",
            ))
        if toggles.enable_linkedin_analysis:
            tasks.append(SearchTask(
                query=f'site:linkedin.com/jobs "{company_name}" engineer OR developer',
                purpose="Find hiring signals.",
                category="linkedin",
            ))
        return tasks
