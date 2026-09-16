"""
Phase 2: Agentic trigger event discovery using the Browser-Use library.

This is the fallback stage — invoked only when Phase 1 (HTTP-based discovery
in trigger_http.py) fails to find a high-confidence trigger event. It uses
a headless browser + LLM agent for JavaScript-heavy sites and complex navigation.

Optimizations over raw browser-use:
- Receives Phase 1 context (URLs already tried) to avoid redundant navigation
- DOM compression strips SVGs, scripts, styles before LLM sees the page
- Reduced max_steps (6 instead of 10) since Phase 1 covers the easy paths
- Rate-limit aware provider routing via ProviderRouter
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Literal
from urllib.parse import urlparse

import structlog
from browser_use.llm.base import ChatInvokeCompletion
from browser_use.llm.openai.chat import ChatOpenAI
from pydantic import BaseModel

from lead_enrich.config import Settings
from lead_enrich.models import TriggerEvent
from lead_enrich.rate_limiter import ProviderRouter

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
    base_domain: str = "",
) -> float:
    """
    Compute grounded confidence for a discovered trigger event.

    Strict grounding rules:
    - If found=False or empty summary: 0.0
    - If source_url is absent or a bare homepage without proof: capped hard at <= 0.30
    - If source_url was NOT specifically reached/visited: capped hard at <= 0.30
    - If summary keywords do NOT appear in the visited content: capped hard at <= 0.30
    - Only corroborated events on specifically visited announcement pages score >= 0.70
    """
    if not event_data.found or not event_data.summary:
        return 0.0

    source_url = (event_data.source_url or "").strip()
    if not source_url:
        return 0.25

    parsed_src = urlparse(source_url)
    path = parsed_src.path.strip("/")
    is_bare_homepage = path in ("", "index.html", "index.htm", "home", "en", "us")

    target_text = extracted_text.lower()
    # Verify that the specific URL was actually navigated to during the run
    src_clean = source_url.rstrip("/")
    was_visited = False
    for u in visited_urls:
        u_clean = u.rstrip("/")
        if src_clean == u_clean:
            was_visited = True
            break
        if not is_bare_homepage and (src_clean in u_clean or u_clean in src_clean):
            was_visited = True
            break

    if not was_visited and not is_bare_homepage:
        if src_clean.lower() in target_text:
            was_visited = True

    if not was_visited:
        return 0.30

    brand = _extract_host(base_domain).split(".")[0].lower() if base_domain else ""
    summary_words = [
        w.lower().strip("$")
        for w in re.findall(r"[a-zA-Z0-9$]+", event_data.summary)
        if len(w.strip("$")) >= 2
        and w.lower() not in COMMON_STOPWORDS
        and w.lower() != brand
        and not w.lower().isdigit()
    ]

    if not summary_words:
        return 0.30

    # Bare homepage citations are not specific announcement sources; cap hard at <= 0.30
    if is_bare_homepage:
        return 0.30

    page_words = set(re.findall(r"\b[a-z0-9$]+\b", target_text))
    matches = [w for w in summary_words if w in page_words]
    overlap_ratio = len(matches) / len(summary_words) if summary_words else 0.0

    # Summary content must substantively appear in the visited page text
    if len(matches) < 2 or overlap_ratio < 0.25:
        return 0.30

    score = 0.70
    if len(matches) >= 3 and overlap_ratio >= 0.40:
        score += 0.10
    if event_data.estimated_date and any(c.isdigit() for c in event_data.estimated_date):
        score += 0.10

    return min(round(score, 2), 0.95)


class ChatGroqOpenAI(ChatOpenAI):
    """OpenAI-compatible wrapper for Groq that bypasses response_format=json_schema.

    Groq's compound models (e.g. groq/compound) have high TPM (70k+) but do not
    support OpenAI's response_format={'type': 'json_schema'}. This wrapper uses
    dont_force_structured_output=True and add_schema_to_system_prompt=True,
    then parses and normalizes the generated JSON so Browser-Use Agent works seamlessly.
    """

    async def ainvoke(self, messages, output_format=None, **kwargs):
        if output_format is not None and self.dont_force_structured_output:
            json_reminder = (
                "\n\nCRITICAL: You must return ONLY a raw JSON object adhering to the schema. "
                "Do NOT output conversational prose, thoughts, or markdown commentary outside JSON."
            )
            augmented_messages = list(messages)
            if augmented_messages and hasattr(augmented_messages[-1], "content"):
                from copy import copy

                last_msg = copy(augmented_messages[-1])
                last_msg.content = (last_msg.content or "") + json_reminder
                augmented_messages[-1] = last_msg
            else:
                augmented_messages = messages

            comp = await super().ainvoke(augmented_messages, output_format=None, **kwargs)
            text = (comp.completion or "").strip()
            code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if code_match:
                text = code_match.group(1)
            else:
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    text = match.group(0)
            try:
                import json

                data = json.loads(text)
                if isinstance(data, dict):
                    if "action" in data:
                        for act in data.get("action", []):
                            if "done" in act and isinstance(act["done"], dict):
                                if "text" not in act["done"]:
                                    act["done"]["text"] = str(
                                        act["done"].get("output") or act["done"].get("data") or ""
                                    )
                    elif any(k in data for k in ("found", "summary", "event_type", "source_url")):
                        data = {
                            "thinking": "Extraction complete.",
                            "action": [{"done": {"text": json.dumps(data)}}],
                        }
                parsed = output_format.model_validate(data)
            except Exception:
                try:
                    parsed = output_format.model_validate_json(text)
                except Exception:
                    parsed = output_format.model_validate(
                        {
                            "thinking": text[:200] if text else "Analyzing page...",
                            "action": [{"wait": {"seconds": 2}}],
                        }
                    )

            return ChatInvokeCompletion(
                completion=parsed,
                usage=comp.usage,
                stop_reason=comp.stop_reason,
            )
        return await super().ainvoke(messages, output_format=output_format, **kwargs)


# Global semaphore allows concurrent Browser-Use agents up to batch capacity
_trigger_semaphore = asyncio.Semaphore(5)


async def _run_browser_use_agent(
    clean_domain: str,
    settings: Settings,
    provider: str = "both",
    verbose: bool = False,
    phase1_urls_tried: list[str] | None = None,
    router: ProviderRouter | None = None,
) -> tuple[TriggerEvent | None, str]:
    """Execute the Browser-Use agent with step and external domain constraints.

    Phase 2 only — called when Phase 1 HTTP scraping didn't find anything.
    Accepts phase1_urls_tried so the agent skips paths already probed.
    """
    import logging

    # Suppress verbose Browser-Use log spam unless explicitly requested
    target_level = logging.INFO if verbose else logging.WARNING
    for log_name in ["browser_use", "Agent", "BrowserSession", "tools", "service"]:
        logging.getLogger(log_name).setLevel(target_level)

    from browser_use import Agent, BrowserProfile, BrowserSession

    # 1. Initialize LLM based on provider selection
    llm = None
    fallback_llm = None

    has_openrouter = bool(settings.openrouter_api_key and settings.openrouter_api_key.strip())
    has_groq = bool(settings.groq_api_key and settings.groq_api_key.strip())

    if provider in ("both", "openrouter") and has_openrouter:
        from browser_use.llm import ChatOpenRouter

        llm = ChatOpenRouter(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            extra_body={"max_tokens": 1500},
        )
        if provider == "both" and has_groq:
            fallback_llm = ChatGroqOpenAI(
                model=settings.groq_trigger_model,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                dont_force_structured_output=True,
                add_schema_to_system_prompt=True,
                max_completion_tokens=1500,
            )

    if llm is None and provider in ("both", "groq") and has_groq:
        llm = ChatGroqOpenAI(
            model=settings.groq_trigger_model,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            dont_force_structured_output=True,
            add_schema_to_system_prompt=True,
            max_completion_tokens=1500,
        )

    if llm is None:
        log.info("trigger_agent_skipped_no_key", domain=clean_domain, provider=provider)
        return None, "skipped"

    # Determine whether the active LLM supports json_schema structured outputs.
    # groq/compound has 70K TPM (great!) but doesn't support response_format json_schema.
    # When it's the primary or only LLM, we skip output_model_schema and rely on prompt
    # instructions + the manual JSON parsing fallback below.
    active_model = (
        settings.groq_trigger_model
        if (llm and not has_openrouter) or provider == "groq"
        else settings.openrouter_model
    )
    use_structured_output = "compound" not in active_model

    # 2. Configure headless browser session
    profile = BrowserProfile(
        headless=True,
        enable_default_extensions=False,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    session = BrowserSession(browser_profile=profile)

    # Build context about URLs already probed by Phase 1 (HTTP scraping)
    skip_note = ""
    if phase1_urls_tried:
        skip_paths = ", ".join(phase1_urls_tried[:5])
        skip_note = (
            f"NOTE: These URLs were already checked and had no trigger events: {skip_paths}. "
            f"Do NOT revisit them.\n\n"
        )

    task_prompt = (
        f"Find the single most recent trigger event for {clean_domain} — prioritize FUNDING "
        f"ROUNDS (Series A/B/C/D, seed, raised $X), then leadership changes, then product news. "
        f"Published in the last 12 months.\n\n"
        f"{skip_note}"
        f"STRATEGY (try each step in order, stop as soon as you find a qualifying event):\n"
        f"1. On homepage, look for nav links: Blog, News, Press, Newsroom, Company, or About. "
        f"Click the most promising one.\n"
        f"2. If no nav link, try navigating to: https://{clean_domain}/blog then "
        f"https://{clean_domain}/news — stop at first that loads.\n"
        f"3. If none exist, do ONE Google search: "
        f"'{clean_domain} funding OR raised OR \"Series\" site:techcrunch.com' "
        f"and click top result.\n"
        f"4. On article page, extract headline, date, and URL, then call done.\n\n"
        f"RULES:\n"
        f"- source_url MUST be the specific blog post or press article URL, NOT the homepage.\n"
        f"- Look for dollar amounts, round names (Seed, Series A/B/C), investor names.\n"
        f"- Be efficient — do NOT click around aimlessly. Each step costs tokens.\n"
        f"- If after all steps above you find nothing qualifying, call done with found=False.\n\n"
        f"OUTPUT FORMAT — when calling done, return ONLY this JSON:\n"
        f'{{"found": true/false, "event_type": "funding"|"leadership_change"|"product_news"|null, '
        f'"summary": "1-2 sentence summary"|null, "source_url": "https://..."|null, '
        f'"estimated_date": "Month YYYY"|null}}'
    )

    # External domain hop enforcement — allow Google + 1 news site + target domain
    allowed_external_limit = 3
    external_domains_seen: set[str] = set()
    should_stop = False

    async def _should_stop_callback() -> bool:
        return should_stop

    async def _on_step_end(agent: Agent) -> None:
        nonlocal should_stop
        for u in agent.history.urls():
            if _is_external_domain(u, clean_domain):
                external_domains_seen.add(_extract_host(u))
                if len(external_domains_seen) > allowed_external_limit:
                    log.info(
                        "trigger_agent_external_hop_limit_hit",
                        domain=clean_domain,
                        external_domains=list(external_domains_seen),
                    )
                    should_stop = True
                    try:
                        stop_res = agent.stop()
                        if asyncio.iscoroutine(stop_res):
                            await stop_res
                    except Exception:
                        pass
                    break

    agent_kwargs = dict(
        task=task_prompt,
        llm=llm,
        fallback_llm=fallback_llm,
        browser_session=session,
        use_vision=False,
        flash_mode=True,
        initial_actions=[{"navigate": {"url": f"https://{clean_domain}", "new_tab": False}}],
        max_actions_per_step=1,
        register_should_stop_callback=_should_stop_callback,
    )
    # Only enforce json_schema when the LLM supports it; otherwise rely on prompt + fallback parsing
    if use_structured_output:
        agent_kwargs["output_model_schema"] = TriggerEventOutput

    agent = Agent(**agent_kwargs)

    try:
        # Enforce max actions hard limit in code
        history = await agent.run(max_steps=settings.trigger_max_steps, on_step_end=_on_step_end)

        # Retrieve structured output from Browser-Use
        output_data: TriggerEventOutput | None = None
        if use_structured_output:
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
        confidence = compute_trigger_confidence(
            output_data, visited_urls, extracted_text, base_domain=clean_domain
        )

        event = TriggerEvent(
            found=output_data.found,
            event_type=output_data.event_type if output_data.found else None,
            summary=output_data.summary if output_data.found else None,
            source_url=output_data.source_url if output_data.found else None,
            estimated_date=output_data.estimated_date if output_data.found else None,
            confidence=confidence,
            trigger_phase="agent",
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
    provider: str = "both",
    verbose: bool = False,
    phase1_urls_tried: list[str] | None = None,
    router: ProviderRouter | None = None,
) -> tuple[TriggerEvent | None, str, float]:
    """
    Phase 2: Discover trigger events via Browser-Use agent.

    Only called when Phase 1 (HTTP scraping) fails. Receives the URLs
    that Phase 1 already tried so the agent doesn't repeat them.

    Args:
        provider: Which LLM backend to use — "both", "openrouter", or "groq".
        phase1_urls_tried: URLs already probed by Phase 1 (skipped by agent).
        router: ProviderRouter for rate-limit aware LLM selection.

    Returns:
        (trigger_event, status, duration_seconds)
        where status is "completed", "timeout", "error", or "skipped".
    """
    clean_domain = _extract_host(domain) or domain
    start_time = time.monotonic()

    # Graceful degradation if neither OpenRouter nor Groq API key is configured
    has_key = bool(
        (settings.openrouter_api_key and settings.openrouter_api_key.strip())
        or (settings.groq_api_key and settings.groq_api_key.strip())
    )
    if not has_key:
        log.info("trigger_agent_skipped_no_key", domain=clean_domain)
        return None, "skipped", 0.0

    try:
        async with _trigger_semaphore:
            event, status = await asyncio.wait_for(
                _run_browser_use_agent(
                    clean_domain,
                    settings,
                    provider=provider,
                    verbose=verbose,
                    phase1_urls_tried=phase1_urls_tried,
                    router=router,
                ),
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
