"""
CLI entrypoint and pipeline orchestrator.

This is where the pieces come together: for each domain, we discover URLs,
fetch pages, preprocess content, extract structured data, enrich with search,
and score confidence — all with hard timeouts and per-domain error isolation.

Usage:
    python -m lead_enrich --domains "postman.com,supabase.com,vapi.ai"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime

import structlog
from rich.console import Console

from lead_enrich.browser import discover_urls, fetch_all_pages, normalize_domain
from lead_enrich.config import Settings, load_settings
from lead_enrich.cost_tracker import print_cost_report
from lead_enrich.enricher import enrich_linkedin_urls
from lead_enrich.extractor import extract_company_intel
from lead_enrich.models import DomainResult, ProcessingStatus
from lead_enrich.preprocessor import prepare_llm_input
from lead_enrich.scorer import compute_confidence
from lead_enrich.writer import write_run_output

# Ensure stdout and stderr use blocking I/O so logging writes never raise
# BlockingIOError (Errno 35) when Playwright/subprocesses touch file descriptors on macOS.
try:
    os.set_blocking(sys.stdout.fileno(), True)
    os.set_blocking(sys.stderr.fileno(), True)
except Exception:
    pass


class SafeStream:
    """Wrapper around stdout that handles non-blocking pipes and prevents BlockingIOError."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, s: str) -> int:
        try:
            return self._stream.write(s)
        except BlockingIOError:
            try:
                os.set_blocking(self._stream.fileno(), True)
                return self._stream.write(s)
            except Exception:
                return len(s)
        except Exception:
            return len(s)

    def flush(self) -> None:
        try:
            self._stream.flush()
        except Exception:
            pass


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=SafeStream(sys.stdout)),
)

log = structlog.get_logger()
console = Console()


async def process_domain(domain: str, settings: Settings, browser=None) -> DomainResult:
    """
    Full pipeline for a single domain. Every failure path returns a
    DomainResult — this function never raises.
    """
    clean_domain = normalize_domain(domain) or domain
    start = time.monotonic()
    result = DomainResult(domain=clean_domain)

    try:
        # Stage 1 & 2: Discover and fetch pages (network/retrieval stage)
        t_fetch_start = time.monotonic()
        urls = await discover_urls(clean_domain, settings, browser=browser)
        result.urls_discovered = urls

        if not urls:
            result.status = ProcessingStatus.FAILED
            result.error_reason = "No URLs discovered — site may be unreachable"
            result.timings.fetch_s = round(time.monotonic() - t_fetch_start, 2)
            result.timings.total_s = round(time.monotonic() - start, 2)
            result.processing_time_s = result.timings.total_s
            return result

        pages = await fetch_all_pages(urls, clean_domain, settings, browser=browser)
        result.timings.fetch_s = round(time.monotonic() - t_fetch_start, 2)
        result.pages_fetched = sum(1 for p in pages if not p.error)
        log.info(
            "stage_fetch_complete",
            domain=clean_domain,
            duration_s=result.timings.fetch_s,
            pages=result.pages_fetched,
        )

        if result.pages_fetched == 0:
            result.status = ProcessingStatus.FAILED
            result.error_reason = "All page fetches failed"
            result.timings.total_s = round(time.monotonic() - start, 2)
            result.processing_time_s = result.timings.total_s
            return result

        # Collect emails found across all pages
        all_emails = []
        for page in pages:
            all_emails.extend(page.emails)

        # Stage 3: Preprocess content for the LLM
        t_preproc_start = time.monotonic()
        llm_input = prepare_llm_input(pages, settings.token_budget)
        result.timings.preprocess_s = round(time.monotonic() - t_preproc_start, 3)
        log.info(
            "stage_preprocess_complete",
            domain=clean_domain,
            duration_s=result.timings.preprocess_s,
        )

        if not llm_input.strip():
            result.status = ProcessingStatus.FAILED
            result.error_reason = "No usable text content after preprocessing"
            result.timings.total_s = round(time.monotonic() - start, 2)
            result.processing_time_s = result.timings.total_s
            return result

        # Stage 4: LLM extraction
        t_llm_start = time.monotonic()
        intel, token_usage = await extract_company_intel(llm_input, clean_domain, settings)
        result.timings.llm_s = round(time.monotonic() - t_llm_start, 2)
        result.token_usage = token_usage
        log.info(
            "stage_llm_complete",
            domain=clean_domain,
            duration_s=result.timings.llm_s,
            tokens=token_usage.total_tokens,
        )

        # Merge emails found by browser with those the LLM found
        browser_emails = set(all_emails)
        llm_emails = set(intel.contact_emails)
        intel.contact_emails = sorted(browser_emails | llm_emails)

        # Stage 5: Enrich with LinkedIn search (and external founder lookup if missing)
        t_enrich_start = time.monotonic()
        intel = await enrich_linkedin_urls(intel, clean_domain, settings)
        result.timings.enrich_s = round(time.monotonic() - t_enrich_start, 2)
        log.info("stage_enrich_complete", domain=clean_domain, duration_s=result.timings.enrich_s)

        # Stage 6: Compute blended confidence score
        intel.confidence_score = compute_confidence(intel)

        result.intel = intel
        result.status = ProcessingStatus.SUCCESS

        # Mark as partial if we're missing key fields
        if not intel.company_overview or not intel.target_audience:
            result.status = ProcessingStatus.PARTIAL

    except TimeoutError:
        result.status = ProcessingStatus.FAILED
        result.error_reason = f"Domain timeout ({settings.domain_timeout_s}s ceiling exceeded)"
        log.error("domain_timeout", domain=clean_domain)

    except Exception as exc:
        # Catch-all — no single domain should kill the batch
        result.status = ProcessingStatus.FAILED
        result.error_reason = f"Unexpected error: {type(exc).__name__}: {str(exc)}"
        log.error("domain_error", domain=clean_domain, error=str(exc), exc_info=True)

    result.timings.total_s = round(time.monotonic() - start, 2)
    result.processing_time_s = result.timings.total_s
    return result


async def run_pipeline(domains: list[str], settings: Settings) -> list[DomainResult]:
    """
    Process multiple domains concurrently with a semaphore and per-domain timeouts.

    Shares a single Chromium process across domains for ultra-fast startup.
    Uses asyncio.gather with explicit per-task wrapping — NOT return_exceptions=True,
    because we want each domain to produce a proper DomainResult even on failure,
    not a raw exception object.
    """
    semaphore = asyncio.Semaphore(settings.max_concurrent_domains)
    clean_domains = [normalize_domain(d) or d for d in domains]

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        try:
            os.set_blocking(sys.stdout.fileno(), True)
            os.set_blocking(sys.stderr.fileno(), True)
        except Exception:
            pass
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        async def _bounded(domain: str) -> DomainResult:
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        process_domain(domain, settings, browser=browser),
                        timeout=settings.domain_timeout_s,
                    )
                except TimeoutError:
                    return DomainResult(
                        domain=domain,
                        status=ProcessingStatus.FAILED,
                        error_reason=f"Hard timeout ({settings.domain_timeout_s}s)",
                    )
                except Exception as exc:
                    return DomainResult(
                        domain=domain,
                        status=ProcessingStatus.FAILED,
                        error_reason=f"Unhandled: {type(exc).__name__}: {str(exc)}",
                    )

        results = await asyncio.gather(*[_bounded(d) for d in clean_domains])
        await browser.close()

    return list(results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Autonomous lead enrichment agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--domains",
        type=str,
        required=True,
        help='Comma-separated list of domains, e.g. "postman.com,supabase.com,vapi.ai"',
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]

    if not domains:
        console.print("[red]No domains provided.[/red]")
        return

    console.print("\n[bold]Lead Enrichment Agent[/bold]")
    console.print(f"Processing {len(domains)} domain(s): {', '.join(domains)}\n")

    settings = load_settings()
    start = time.monotonic()

    results = await run_pipeline(domains, settings)

    elapsed = round(time.monotonic() - start, 1)
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Write run-specific timestamped files, manifest, and update all_leads archive
    run_json, run_csv, manifest_path = write_run_output(
        results=results,
        output_dir=settings.output_dir,
        run_id=run_id,
        model_name=settings.llm_model,
        total_duration_s=elapsed,
    )

    # Print summary
    console.print(f"\n[bold green]Done in {elapsed}s[/bold green] (Run: [cyan]{run_id}[/cyan])")
    console.print(f"  Run JSON:  {run_json}")
    console.print(f"  Run CSV:   {run_csv}")
    console.print(f"  Telemetry: {manifest_path}")
    console.print(f"  Master:    {settings.output_dir / 'all_leads.csv'}")

    succeeded = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
    partial = sum(1 for r in results if r.status == ProcessingStatus.PARTIAL)
    failed = sum(1 for r in results if r.status == ProcessingStatus.FAILED)
    console.print(
        f"  Results: [green]{succeeded} success[/green], "
        f"[yellow]{partial} partial[/yellow], "
        f"[red]{failed} failed[/red]"
    )

    # Cost report
    print_cost_report(results)


if __name__ == "__main__":
    asyncio.run(main())
