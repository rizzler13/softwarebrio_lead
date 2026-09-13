"""
Agentic trigger event discovery stage using the Browser-Use library.

This stage runs on every domain in parallel with the deterministic LinkedIn enrichment.
It answers: "Is there a recent, genuine trigger event for this company — funding,
leadership change, or major product/company news — published within the last 12 months?"
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Literal
from urllib.parse import urlparse

import structlog
from pydantic import BaseModel

from lead_enrich.config import Settings
from lead_enrich.models import TriggerEvent

log = structlog.get_logger()

COMMON_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "all",
    "also",
    "and",
    "another",
    "any",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "came",
    "come",
    "could",
    "each",
    "from",
    "have",
    "having",
    "here",
    "into",
    "just",
    "like",
    "make",
    "many",
    "more",
    "most",
    "much",
    "only",
    "other",
    "over",
    "said",
    "same",
    "some",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "time",
    "very",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "year",
    "years",
    "company",
}


class TriggerEventOutput(BaseModel):
    """Pydantic model passed to Browser-Use for structured output extraction."""

    found: bool = False
    event_type: Literal["funding", "leadership_change", "product_news", "other"] | None = None
    summary: str | None = None
    source_url: str | None = None
    estimated_date: str | None = None


def _extract_host(url_or_domain: str) -> str:
    """Normalize a URL or domain string to lowercase bare host without www."""
    if "://" in url_or_domain:
        host = urlparse(url_or_domain).netloc.lower()
    else:
        host = url_or_domain.lower()
    if ":" in host:
        host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_external_domain(url: str, base_domain: str) -> bool:
    """Check whether a URL belongs to a foreign host (outside base domain)."""
    host = _extract_host(url)
    base = _extract_host(base_domain)
    if not host or not base:
        return False
    return host != base and not host.endswith("." + base)


def compute_trigger_confidence(
    event_data: TriggerEventOutput,
    visited_urls: list[str],
    extracted_text: str = "",
) -> float:
    """
    Compute grounded confidence for a discovered trigger event.

    Rules:
    - If found=False or empty summary: 0.0
    - If source_url was NOT reached/visited: capped at 0.30
    - If source_url was reached: base 0.70 + keyword overlap bonus (0.10) + valid date (0.10)
    """
    if not event_data.found or not event_data.summary:
        return 0.0

    source_url = event_data.source_url or ""
    visited_hosts = {_extract_host(u) for u in visited_urls if u}

    # Verify reachability of source_url
    was_visited = False
    if source_url:
        src_host = _extract_host(source_url)
        was_visited = src_host in visited_hosts or any(
            source_url in u or u in source_url for u in visited_urls
        )

    if not source_url or not was_visited:
        return 0.30

    # Keyword overlap between summary and visited page context
    summary_words = {
        w.lower()
        for w in re.findall(r"[a-zA-Z]{4,}", event_data.summary)
        if w.lower() not in COMMON_STOPWORDS
    }

    if not summary_words:
        return 0.50

    target_text = (extracted_text + " " + source_url).lower()
    matches = sum(1 for w in summary_words if w in target_text)
    overlap_ratio = matches / len(summary_words) if summary_words else 0.0

    score = 0.70
    if overlap_ratio >= 0.25 or matches >= 3:
        score += 0.10
    if event_data.estimated_date and any(c.isdigit() for c in event_data.estimated_date):
        score += 0.10

    return min(round(score, 2), 0.95)


async def _run_browser_use_agent(
    clean_domain: str,
    settings: Settings,
) -> tuple[TriggerEvent | None, str]:
    """Execute the Browser-Use agent with step and external domain constraints."""
    from browser_use import Agent, BrowserProfile, BrowserSession
    from browser_use.llm import ChatOpenRouter

    # 1. Initialize OpenRouter LLM for Browser-Use
    llm = ChatOpenRouter(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
    )

    # 2. Configure headless browser session
    profile = BrowserProfile(
        headless=True,
        enable_default_extensions=False,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    session = BrowserSession(browser_profile=profile)

    task_prompt = (
        f"Starting from https://{clean_domain}, find the single most recent, genuine company "
        "news item (funding round, leadership change, or major product/company announcement) "
        "published within roughly the last 12 months. Check the homepage navigation or footer "
        "for News, Blog, Press, or Changelog links. If found, navigate there, identify the top "
        "qualifying headline, date, and source URL, and immediately call done with your findings. "
        "If the homepage links out to an external press article, you may follow one external link. "
        "Do not fabricate a date or event if none is found — return found=False instead."
    )

    # External domain hop enforcement state
    external_domains_seen: set[str] = set()
    should_stop = False

    async def _should_stop_callback() -> bool:
        return should_stop

    async def _on_step_end(agent: Agent) -> None:
        nonlocal should_stop
        for u in agent.history.urls():
            if _is_external_domain(u, clean_domain):
                external_domains_seen.add(_extract_host(u))
                if len(external_domains_seen) > 1:
                    log.info(
                        "trigger_agent_external_hop_limit_hit",
                        domain=clean_domain,
                        external_domains=list(external_domains_seen),
                    )
                    should_stop = True
                    await agent.stop()
                    break

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser_session=session,
        use_vision=False,
        output_model_schema=TriggerEventOutput,
        max_actions_per_step=1,
        register_should_stop_callback=_should_stop_callback,
    )

    try:
        # Enforce max 8 actions hard limit in code
        history = await agent.run(max_steps=settings.trigger_max_steps, on_step_end=_on_step_end)

        # Retrieve structured output from Browser-Use
        output_data: TriggerEventOutput | None = None
        try:
            output_data = history.get_structured_output(TriggerEventOutput)
        except Exception:
            pass

        if not output_data:
            # Fallback: attempt json parsing of final result
            final_res = history.final_result()
            if final_res:
                try:
                    import json

                    parsed = json.loads(final_res)
                    if isinstance(parsed, dict):
                        output_data = TriggerEventOutput.model_validate(parsed)
                except Exception:
                    pass

        if not output_data:
            output_data = TriggerEventOutput(found=False)

        # Grounded confidence scoring
        visited_urls = history.urls()
        extracted_text = " ".join(history.extracted_content() or [])
        confidence = compute_trigger_confidence(output_data, visited_urls, extracted_text)

        event = TriggerEvent(
            found=output_data.found,
            event_type=output_data.event_type if output_data.found else None,
            summary=output_data.summary if output_data.found else None,
            source_url=output_data.source_url if output_data.found else None,
            estimated_date=output_data.estimated_date if output_data.found else None,
            confidence=confidence,
        )
        return event, "completed"

    finally:
        try:
            await session.close()
        except Exception:
            pass


async def discover_trigger_event(
    domain: str,
    settings: Settings,
) -> tuple[TriggerEvent | None, str, float]:
    """
    Discover recent trigger events for a domain using Browser-Use.

    Returns:
        (trigger_event, status, duration_seconds)
        where status is "completed", "timeout", "error", or "skipped".
    """
    clean_domain = _extract_host(domain) or domain
    start_time = time.monotonic()

    # Graceful degradation if OpenRouter API key is not configured
    if not settings.openrouter_api_key or not settings.openrouter_api_key.strip():
        log.info("trigger_agent_skipped_no_key", domain=clean_domain)
        return None, "skipped", 0.0

    try:
        event, status = await asyncio.wait_for(
            _run_browser_use_agent(clean_domain, settings),
            timeout=settings.trigger_stage_timeout_s,
        )
        duration = round(time.monotonic() - start_time, 2)
        log.info(
            "trigger_stage_complete",
            domain=clean_domain,
            status=status,
            found=event.found if event else False,
            duration_s=duration,
        )
        return event, status, duration

    except TimeoutError:
        duration = round(time.monotonic() - start_time, 2)
        log.warning(
            "trigger_stage_timeout",
            domain=clean_domain,
            timeout_s=settings.trigger_stage_timeout_s,
            duration_s=duration,
        )
        return None, "timeout", duration

    except Exception as exc:
        duration = round(time.monotonic() - start_time, 2)
        log.warning(
            "trigger_stage_error",
            domain=clean_domain,
            error=str(exc),
            duration_s=duration,
        )
        return None, "error", duration
