"""
Phase 1: Lightweight HTTP-based trigger event discovery.

Attempts to find recent funding, leadership, or product announcements
using plain HTTP requests and regex heuristics — zero LLM tokens consumed.

This module is the first line of defense in the two-phase trigger architecture.
If it finds a high-confidence event, the expensive Browser-Use agent (Phase 2)
is skipped entirely.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import urljoin, urlparse

import aiohttp
import structlog

from lead_enrich.config import Settings
from lead_enrich.models import TriggerEvent

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Regex patterns for funding signal detection
# ---------------------------------------------------------------------------

# Dollar amounts: $5M, $50 million, $120M, $1.2B, $500K
_DOLLAR_PATTERN = re.compile(
    r"\$\s?(\d[\d,.]*)\s*(million|billion|[MBKmb])\b",
    re.IGNORECASE,
)

# Round names: Series A, Series B, Seed, Pre-seed, growth round
_ROUND_PATTERN = re.compile(
    r"\b(seed|pre[- ]?seed|series\s+[A-Fa-f]|growth\s+round|bridge\s+round|"
    r"extension|funding\s+round)\b",
    re.IGNORECASE,
)

# Fundraise verbs: raised, secures, closes, announces
_FUNDRAISE_VERB_PATTERN = re.compile(
    r"\b(raised|raises|secures?d?|closed?s?|announces?\s+(?:a?\s*\$|funding|"
    r"raise|investment|round)|led\s+by|backed\s+by|invested)\b",
    re.IGNORECASE,
)

# Leadership change signals
_LEADERSHIP_PATTERN = re.compile(
    r"\b(appoints?|named|hires?|joins?\s+as|new\s+(?:CEO|CTO|CFO|COO|CPO|CRO|"
    r"chief|president|head\s+of)|steps?\s+down|departs?|succeeds?)\b",
    re.IGNORECASE,
)

# Product / launch signals
_PRODUCT_PATTERN = re.compile(
    r"\b(launches?|launched|unveils?|introduces?|announces?\s+(?:new|general\s+"
    r"availability|GA|beta|partnership|acquisition)|acquires?d?|acquired|"
    r"partners?\s+with)\b",
    re.IGNORECASE,
)

# Date extraction: "September 2026", "Sep 15, 2026", "2026-09-15", etc.
_DATE_PATTERNS = [
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\.?\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
]

# Common blog/news/press paths to probe
_NEWS_PATHS = [
    "/blog",
    "/news",
    "/press",
    "/newsroom",
    "/press-releases",
    "/company/news",
    "/about/news",
    "/resources/blog",
    "/blog/announcements",
]

# User-Agent that doesn't scream "bot"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _strip_html(html: str) -> str:
    """Quick-and-dirty HTML to text conversion without heavy dependencies."""
    # Remove script and style blocks entirely
    text = re.sub(
        r"<(script|style|noscript)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Convert common block elements to newlines
    text = re.sub(
        r"<(?:br|p|div|h[1-6]|li|tr|article|section)[^>]*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = unescape(text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_article_links(html: str, base_url: str) -> list[dict[str, str]]:
    """
    Extract article-like links from a blog/news index page.

    Returns a list of dicts with 'url' and 'text' keys, sorted by
    likelihood of being a recent announcement (funding keywords first).
    """
    # Find all <a> tags with href
    link_pattern = re.compile(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    links = []
    seen_urls = set()

    for match in link_pattern.finditer(html):
        href = match.group(1).strip()
        link_text = _strip_html(match.group(2)).strip()

        if not href or not link_text or len(link_text) < 10:
            continue

        # Resolve relative URLs
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Skip non-HTTP, anchor-only, and obviously non-article URLs
        if parsed.scheme not in ("http", "https"):
            continue
        if full_url in seen_urls:
            continue

        # Prefer links with blog/news/press in the path
        path = parsed.path.lower()
        is_article = any(
            seg in path
            for seg in ("/blog/", "/news/", "/press/", "/post/", "/article/", "/announcements/")
        )
        if not is_article and path.count("/") < 2:
            continue

        seen_urls.add(full_url)
        links.append({"url": full_url, "text": link_text})

    # Sort: funding-related links first, then by position (recency)
    def _funding_score(link: dict) -> int:
        text = link["text"].lower()
        score = 0
        if _DOLLAR_PATTERN.search(text):
            score += 10
        if _ROUND_PATTERN.search(text):
            score += 8
        if _FUNDRAISE_VERB_PATTERN.search(text):
            score += 5
        return -score  # Negative for descending sort

    links.sort(key=_funding_score)
    return links[:10]  # Top 10 candidates


def _score_trigger_text(text: str) -> tuple[float, str, str | None]:
    """
    Score a block of text for trigger event signals.

    Returns (confidence, event_type, extracted_date_string).
    """
    confidence = 0.0
    event_type: str = "other"
    date_str: str | None = None

    text_lower = text.lower()

    # Check for funding signals (highest priority)
    has_dollar = bool(_DOLLAR_PATTERN.search(text))
    has_round = bool(_ROUND_PATTERN.search(text))
    has_fundraise_verb = bool(_FUNDRAISE_VERB_PATTERN.search(text))

    if has_dollar and has_round and has_fundraise_verb:
        confidence = 0.80
        event_type = "funding"
    elif has_dollar and (has_round or has_fundraise_verb):
        confidence = 0.70
        event_type = "funding"
    elif has_round and has_fundraise_verb:
        confidence = 0.65
        event_type = "funding"
    elif has_dollar and any(
        w in text_lower for w in ("fund", "invest", "capital", "venture", "valuation")
    ):
        confidence = 0.55
        event_type = "funding"

    # Leadership change signals
    if confidence < 0.50 and _LEADERSHIP_PATTERN.search(text):
        leader_terms = sum(
            1
            for t in ("ceo", "cto", "cfo", "coo", "chief", "president", "founder")
            if t in text_lower
        )
        if leader_terms >= 1:
            confidence = max(confidence, 0.55)
            event_type = "leadership_change"

    # Product / launch signals
    if confidence < 0.50 and _PRODUCT_PATTERN.search(text):
        confidence = max(confidence, 0.45)
        event_type = "product_news"

    # Extract date
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            date_str = match.group(0)
            break

    # Date recency bonus: if date is within last 12 months, boost confidence
    if date_str and confidence > 0:
        try:
            # Try parsing common formats
            for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%B %Y", "%Y-%m-%d"):
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    if datetime.now() - parsed_date < timedelta(days=365):
                        confidence = min(confidence + 0.05, 0.80)
                    elif datetime.now() - parsed_date > timedelta(days=730):
                        confidence *= 0.6  # Old news penalty
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    return confidence, event_type, date_str


def _extract_summary(text: str, max_chars: int = 200) -> str:
    """Extract a clean 1-2 sentence summary from article text."""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary_parts = []
    char_count = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue
        # Skip navigation-like sentences
        if sentence.lower().startswith(("skip to", "menu", "search", "sign", "log in", "cookie")):
            continue
        summary_parts.append(sentence)
        char_count += len(sentence)
        if char_count >= max_chars or len(summary_parts) >= 2:
            break

    return " ".join(summary_parts)[:300] if summary_parts else ""


async def _fetch_page(
    session: aiohttp.ClientSession,
    url: str,
    timeout_s: float = 8.0,
) -> str | None:
    """Fetch a page and return its HTML, or None on failure."""
    try:
        async with session.get(
            url,
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
            allow_redirects=True,
            ssl=False,
        ) as response:
            if response.status >= 400:
                return None
            # Only process HTML responses
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            return await response.text(encoding="utf-8", errors="replace")
    except Exception:
        return None


async def discover_trigger_http(
    domain: str,
    settings: Settings,
) -> tuple[TriggerEvent | None, str, float]:
    """
    Phase 1: Discover trigger events using plain HTTP + regex heuristics.

    Zero LLM tokens consumed. Tries blog/news/press pages first, then
    falls back to Tavily search if available.

    Returns:
        (trigger_event, status, duration_seconds)
        where status is "completed", "no_signal", or "error".
    """
    start = time.monotonic()
    base_url = f"https://{domain}"
    best_event: TriggerEvent | None = None
    best_confidence = 0.0
    urls_tried: list[str] = []

    try:
        connector = aiohttp.TCPConnector(limit=5, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            # 1. Probe known blog/news/press paths in parallel
            probe_urls = [f"{base_url}{path}" for path in _NEWS_PATHS]
            fetch_tasks = [_fetch_page(session, url, timeout_s=6.0) for url in probe_urls]
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            # Find pages that actually returned content
            live_pages: list[tuple[str, str]] = []
            for url, result in zip(probe_urls, results):
                if isinstance(result, str) and result and len(result) > 500:
                    live_pages.append((url, result))

            # 2. For each live page, extract article links and score them
            for page_url, page_html in live_pages:
                urls_tried.append(page_url)
                article_links = _extract_article_links(page_html, page_url)

                if not article_links:
                    # Try scoring the index page itself (some sites list news inline)
                    page_text = _strip_html(page_html)
                    conf, etype, date_str = _score_trigger_text(page_text[:3000])
                    if conf > best_confidence:
                        best_confidence = conf
                        best_event = TriggerEvent(
                            found=True,
                            event_type=etype,
                            summary=_extract_summary(page_text),
                            source_url=page_url,
                            estimated_date=date_str,
                            confidence=round(conf, 2),
                            trigger_phase="http",
                        )
                    continue

                # Fetch top 3 article candidates in parallel
                top_articles = article_links[:3]
                article_tasks = [
                    _fetch_page(session, link["url"], timeout_s=6.0) for link in top_articles
                ]
                article_results = await asyncio.gather(*article_tasks, return_exceptions=True)

                for link, article_html in zip(top_articles, article_results):
                    if not isinstance(article_html, str) or not article_html:
                        continue

                    urls_tried.append(link["url"])
                    article_text = _strip_html(article_html)

                    # Score using both the link text (headline) and article body
                    combined_text = f"{link['text']}\n{article_text[:2000]}"
                    conf, etype, date_str = _score_trigger_text(combined_text)

                    if conf > best_confidence:
                        best_confidence = conf
                        summary = _extract_summary(article_text)
                        if not summary:
                            summary = link["text"]

                        best_event = TriggerEvent(
                            found=True,
                            event_type=etype,
                            summary=summary,
                            source_url=link["url"],
                            estimated_date=date_str,
                            confidence=round(conf, 2),
                            trigger_phase="http",
                        )

                # Early exit if we found a strong signal
                if best_confidence >= 0.70:
                    break

            # 3. If no strong signal from direct pages, try Tavily search (if available)
            if best_confidence < 0.60 and settings.tavily_api_key:
                try:
                    from tavily import AsyncTavilyClient

                    tavily = AsyncTavilyClient(api_key=settings.tavily_api_key)
                    search_query = f'"{domain}" funding OR raised OR "Series" OR acquired'
                    search_results = await tavily.search(
                        query=search_query,
                        max_results=5,
                        search_depth="basic",
                    )

                    for result in search_results.get("results", []):
                        title = result.get("title", "")
                        content = result.get("content", "")
                        url = result.get("url", "")

                        # Skip the company's own homepage
                        if urlparse(url).netloc.replace("www.", "") == domain:
                            path = urlparse(url).path.strip("/")
                            if not path or path in ("index.html", "home"):
                                continue

                        combined = f"{title}\n{content}"
                        conf, etype, date_str = _score_trigger_text(combined)

                        if conf > best_confidence:
                            best_confidence = conf
                            best_event = TriggerEvent(
                                found=True,
                                event_type=etype,
                                summary=_extract_summary(f"{title}. {content}"),
                                source_url=url,
                                estimated_date=date_str,
                                confidence=round(conf, 2),
                                trigger_phase="http",
                            )

                except Exception as exc:
                    log.debug("trigger_http_tavily_error", domain=domain, error=str(exc))

    except Exception as exc:
        duration = round(time.monotonic() - start, 2)
        log.warning("trigger_http_error", domain=domain, error=str(exc))
        return None, "error", duration

    duration = round(time.monotonic() - start, 2)

    if best_event and best_confidence >= 0.55:
        log.info(
            "trigger_http_found",
            domain=domain,
            event_type=best_event.event_type,
            confidence=best_event.confidence,
            source=best_event.source_url,
            duration_s=duration,
            urls_tried=len(urls_tried),
        )
        return best_event, "completed", duration

    log.info(
        "trigger_http_no_signal",
        domain=domain,
        best_confidence=round(best_confidence, 2),
        duration_s=duration,
        urls_tried=len(urls_tried),
    )
    return None, "no_signal", duration
