"""
Headless browser automation — discovers relevant URLs and fetches page content.

Uses async Playwright because:
- Native async support (no thread pool hacks like Selenium)
- Better JS rendering for modern SPA sites
- Stealth-friendlier out of the box
"""

from __future__ import annotations

import asyncio
import random
import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import structlog
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from lead_enrich.config import Settings
from lead_enrich.models import PageContent

log = structlog.get_logger()

# Keywords that signal a page is worth fetching, with relative importance.
# Higher weight = more likely to contain useful intel for lead enrichment.
PAGE_KEYWORDS: dict[str, int] = {
    "about": 10,
    "team": 10,
    "leadership": 9,
    "people": 8,
    "company": 8,
    "who-we-are": 8,
    "our-story": 7,
    "contact": 7,
    "pricing": 5,
    "careers": 3,
}

# Rotate user agents to avoid trivial bot detection.
# These are real Chrome UAs — nothing exotic.
USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
]


def normalize_domain(raw: str) -> str:
    """
    Clean up user input domains.
    Handles 'https://example.com/about/', 'http://foo.bar', 'baz.com/' -> 'example.com'.
    """
    raw = raw.strip()
    if not raw:
        return ""
    if "://" in raw:
        parsed = urlparse(raw)
        return parsed.netloc.lower().rstrip("/")
    # Handle paths or trailing slashes without protocol: 'example.com/path'
    parsed = urlparse(f"https://{raw}")
    return (parsed.netloc or raw).lower().rstrip("/")


def _score_url(path: str) -> int:
    """Rate how useful a URL path probably is based on keyword overlap."""
    path_lower = path.lower()
    return sum(weight for kw, weight in PAGE_KEYWORDS.items() if kw in path_lower)


def _is_same_domain(href: str, base_domain: str) -> bool:
    """Check if a URL belongs to the same domain (ignore subdomains for now)."""
    try:
        parsed = urlparse(href)
        host = parsed.hostname or ""
        return base_domain in host
    except Exception:
        return False


def _check_robots(base_url: str, path: str) -> bool:
    """Quick robots.txt check — returns True if we're allowed to fetch the path."""
    try:
        rp = RobotFileParser()
        rp.set_url(f"{base_url}/robots.txt")
        rp.read()
        return rp.can_fetch("*", f"{base_url}{path}")
    except Exception:
        # If we can't read robots.txt, assume it's fine
        return True


def _extract_emails(text: str) -> list[str]:
    """Pull email addresses out of page text. Only keeps plausible ones."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found = set(re.findall(pattern, text))
    # Filter out obvious junk (image filenames, etc.)
    return sorted(
        email.lower()
        for email in found
        if not email.endswith((".png", ".jpg", ".svg", ".gif", ".webp"))
    )


# Concurrency limit on concurrent page evaluations to prevent network/CPU saturation
_page_semaphore = asyncio.Semaphore(8)

# Cache homepage content discovered during URL discovery so we don't re-fetch it
_page_cache: dict[str, PageContent] = {}


async def _create_optimized_context(browser):
    """Create a Playwright context that aborts images, fonts, and media for maximum speed."""
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1280, "height": 720},
    )
    # Block heavy binary assets that aren't needed for text extraction
    await context.route(
        "**/*.{png,jpg,jpeg,webp,svg,gif,ico,woff,woff2,ttf,eot,mp4,webm,avi,mp3}",
        lambda route: route.abort(),
    )
    return context


async def discover_urls(domain: str, settings: Settings, browser=None) -> list[str]:
    """
    Hit the homepage, parse nav/footer links, and rank them by relevance.

    Extracts and caches the homepage content directly so subsequent fetches
    don't waste time and bandwidth hitting the homepage a second time.
    """
    domain = normalize_domain(domain)
    base_url = f"https://{domain}"
    discovered: dict[str, int] = {}

    own_browser = False
    pw_instance = None
    if browser is None:
        pw_instance = await async_playwright().start()
        browser = await pw_instance.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        own_browser = True

    try:
        context = await _create_optimized_context(browser)
        page = await context.new_page()

        try:
            await page.goto(
                base_url, wait_until="domcontentloaded", timeout=settings.page_timeout_ms
            )
            # Short wait for JS hydration
            await page.wait_for_timeout(350)

            # Cache homepage text and metadata immediately — saves an entire browser round-trip
            try:
                hp_text = await page.inner_text("body")
                hp_meta = await page.eval_on_selector_all(
                    'meta[name="description"], meta[property="og:description"]',
                    "els => els.map(e => e.content).filter(Boolean)",
                )
                hp_jsonld = await page.eval_on_selector_all(
                    'script[type="application/ld+json"]',
                    "els => els.map(e => e.textContent)",
                )
                hp_combined = hp_text + "\n" + "\n".join(hp_meta) + "\n" + "\n".join(hp_jsonld)
                _page_cache[base_url] = PageContent(
                    url=base_url,
                    text=hp_text,
                    emails=_extract_emails(hp_combined),
                    meta_description=hp_meta[0] if hp_meta else "",
                    status_code=200,
                )
            except Exception as exc:
                log.debug("homepage_early_extract_error", domain=domain, error=str(exc))

            # Grab all links from nav, header, footer, and main content
            links = await page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.href)",
            )

            for href in links:
                if not _is_same_domain(href, domain):
                    continue
                parsed = urlparse(href)
                path = parsed.path.rstrip("/")
                if not path or path == "/":
                    continue
                # Skip obvious non-content paths
                if any(
                    skip in path.lower()
                    for skip in [
                        "/blog",
                        "/docs",
                        "/api",
                        "/login",
                        "/signup",
                        "/register",
                        "/app",
                        "/dashboard",
                        "/legal",
                    ]
                ):
                    continue
                score = _score_url(path)
                if score > 0:
                    full_url = f"{base_url}{path}"
                    discovered[full_url] = max(discovered.get(full_url, 0), score)

        except PlaywrightTimeout:
            log.warning("homepage_timeout", domain=domain)
        except Exception as exc:
            log.warning("homepage_error", domain=domain, error=str(exc))
        finally:
            await context.close()
    finally:
        if own_browser:
            await browser.close()
            if pw_instance:
                await pw_instance.stop()

    # Sort by relevance score, take top 2 high-signal subpages (plus homepage = 3 total)
    ranked = sorted(discovered.items(), key=lambda x: x[1], reverse=True)
    urls = [url for url, _ in ranked[:2]]

    # Fallback: if we didn't find subpages, try common paths
    if len(urls) < 1:
        fallback_paths = ["/about", "/team", "/company"]
        for path in fallback_paths:
            candidate = f"{base_url}{path}"
            if candidate not in urls:
                urls.append(candidate)
                if len(urls) >= 2:
                    break

    # Always include the homepage itself
    if base_url not in urls:
        urls.insert(0, base_url)

    log.info("urls_discovered", domain=domain, count=len(urls), urls=urls)
    return urls


async def fetch_page(url: str, context, settings: Settings) -> PageContent:
    """
    Render a single page and extract its text content.

    If the page was already parsed during URL discovery (e.g. homepage),
    returns the cached PageContent instantly with zero network latency.
    """
    if url in _page_cache:
        return _page_cache.pop(url)

    async with _page_semaphore:
        page = await context.new_page()
        try:
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=settings.page_timeout_ms
            )
            status = response.status if response else 0

            if status >= 400:
                return PageContent(url=url, status_code=status, error=f"HTTP {status}")

            # Extract visible text — inner_text cleanly extracts what a human reads
            text = await page.inner_text("body")

            # Try to grab meta description for extra context
            meta_desc = await page.eval_on_selector_all(
                'meta[name="description"], meta[property="og:description"]',
                "els => els.map(e => e.content).filter(Boolean)",
            )

            # Look for structured data (JSON-LD) that might have team info
            jsonld_texts = await page.eval_on_selector_all(
                'script[type="application/ld+json"]',
                "els => els.map(e => e.textContent)",
            )

            # Combine all text sources
            extra_text = "\n".join(meta_desc) + "\n" + "\n".join(jsonld_texts)
            full_text = text + "\n" + extra_text

            emails = _extract_emails(full_text)

            return PageContent(
                url=url,
                text=text,
                emails=emails,
                meta_description=meta_desc[0] if meta_desc else "",
                status_code=status,
            )

        except PlaywrightTimeout:
            log.warning("page_timeout", url=url)
            return PageContent(url=url, error="timeout")
        except Exception as exc:
            log.warning("page_fetch_error", url=url, error=str(exc))
            return PageContent(url=url, error=str(exc))
        finally:
            await page.close()


async def fetch_all_pages(
    urls: list[str], domain: str, settings: Settings, browser=None
) -> list[PageContent]:
    """
    Fetch multiple pages concurrently from the same domain.

    Shares an optimized browser context across pages and fetches them in parallel.
    """
    own_browser = False
    pw_instance = None
    if browser is None:
        pw_instance = await async_playwright().start()
        browser = await pw_instance.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        own_browser = True

    try:
        context = await _create_optimized_context(browser)
        tasks = [fetch_page(url, context, settings) for url in urls]
        pages = await asyncio.gather(*tasks)
        await context.close()
    finally:
        if own_browser:
            await browser.close()
            if pw_instance:
                await pw_instance.stop()

    successful = sum(1 for p in pages if not p.error)
    log.info("pages_fetched", domain=domain, total=len(pages), successful=successful)
    return list(pages)
