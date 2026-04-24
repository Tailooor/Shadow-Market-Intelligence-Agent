import asyncio
import json
from collections import OrderedDict
from typing import Callable

import httpx
import trafilatura
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
        self.http = httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
                )
            },
        )
        self._semaphore = asyncio.Semaphore(5)

    async def close(self) -> None:
        await self.http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def plan_research(self, company_name: str, toggles: ToolToggles) -> ResearchPlan:
        prompt = f"""
Target company: {company_name}

Tool toggles:
- Reddit search enabled: {toggles.enable_reddit_search}
- LinkedIn analysis enabled: {toggles.enable_linkedin_analysis}
- Reviews analysis enabled: {toggles.enable_reviews_analysis}

Create a high-value research plan for a competitor intelligence workflow.
""".strip()
        result = await self.lead_researcher.run(prompt)
        return result.output

    async def execute_searches(self, plan: ResearchPlan, toggles: ToolToggles, trace: TraceFn) -> list[SearchResult]:
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

        async def _search_one(task: SearchTask) -> None:
            trace(f"Searching for {task.category} evidence: {task.query}")
            try:
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: _ddgs_text(task.query, self.settings.max_search_results_per_task),
                )
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

        await asyncio.gather(*[_search_one(task) for task in filtered_tasks])

        ranked = list(deduped.values())[: self.settings.max_sources_to_analyze]
        trace(f"Collected {len(ranked)} unique URLs for source analysis.")
        return ranked

    async def fetch_source_text(self, source: SearchResult, trace: TraceFn) -> str:
        trace(f"Fetching source: {source.url}")
        try:
            response = await self.http.get(source.url)
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

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def analyze_source(self, company_name: str, plan: ResearchPlan, source: SearchResult, source_text: str) -> SourceAnalysis | None:
        if not source_text.strip():
            return None

        prompt = f"""
Target company: {company_name}
Source category: {source.category}
Source title: {source.title}
Source URL: {source.url}
Search query that found it: {source.query}
Snippet: {source.snippet}

Research plan context (intel gaps and working hypotheses):
{json.dumps([gap.model_dump() for gap in plan.intel_gaps], indent=2)}

Source text:
{source_text}
""".strip()

        result = await self.analyst.run(prompt)
        analysis = result.output
        return analysis.model_copy(
            update={
                "source_title": analysis.source_title or source.title,
                "source_url": analysis.source_url or source.url,
                "category": analysis.category or source.category,
            }
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def synthesize_report(
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
{json.dumps([analysis.model_dump() for analysis in analyses], indent=2)}
""".strip()
        result = await self.synthesis_agent.run(prompt)
        draft = result.output
        return CompetitorReport(
            **draft.model_dump(),
            source_evidence=analyses,
            trace=trace_log,
        )

    async def analyze_sources_parallel(
        self,
        company_name: str,
        plan: ResearchPlan,
        search_results: list[SearchResult],
        trace: TraceFn,
    ) -> list[SourceAnalysis]:
        async def _analyze_one(source: SearchResult) -> SourceAnalysis | None:
            async with self._semaphore:
                source_text = await self.fetch_source_text(source, trace)
                if not source_text.strip():
                    trace(f"Skipped source with no usable text: {source.url}")
                    return None
                trace(f"Analyst agent is extracting signals from {source.title}.")
                try:
                    analysis = await self.analyze_source(company_name, plan, source, source_text)
                    if analysis is not None:
                        trace(f"Captured structured findings from {analysis.source_title} with {analysis.confidence} confidence.")
                    else:
                        trace(f"Analyst skipped {source.title} because the page content was empty.")
                    return analysis
                except Exception as exc:
                    trace(f"Analysis failed for {source.title}: {exc}")
                    return None

        results = await asyncio.gather(*[_analyze_one(source) for source in search_results])
        return [r for r in results if r is not None]

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


def _ddgs_text(query: str, max_results: int):
    with DDGS() as ddgs:
        return ddgs.text(query, max_results=max_results)
