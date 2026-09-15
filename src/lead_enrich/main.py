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
import subprocess
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
from lead_enrich.trigger_agent import discover_trigger_event
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


def configure_logging(verbose: bool = False) -> None:
    """Configure structlog and standard logging levels based on verbosity."""
    import logging

    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=SafeStream(sys.stdout)),
    )

    # Suppress verbose external loggers unless requested
    ext_level = logging.INFO if verbose else logging.WARNING
    for log_name in [
        "browser_use",
        "Agent",
        "BrowserSession",
        "tools",
        "service",
        "playwright",
        "cdp_use",
    ]:
        logging.getLogger(log_name).setLevel(ext_level)


configure_logging(verbose=False)
log = structlog.get_logger()
console = Console(highlight=False)


async def process_domain(
    domain: str,
    settings: Settings,
    browser=None,
    agentic: bool = False,
    provider: str = "both",
    verbose: bool = False,
) -> DomainResult:
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

        # Stage 5: Enrich with LinkedIn search (and discover trigger event if agentic)
        async def _timed_enrich():
            t0 = time.monotonic()
            enriched_intel = await enrich_linkedin_urls(intel, clean_domain, settings)
            duration = round(time.monotonic() - t0, 2)
            return enriched_intel, duration

        enrich_task = asyncio.create_task(_timed_enrich())

        if agentic:
            trigger_task = asyncio.create_task(
                discover_trigger_event(clean_domain, settings, provider=provider, verbose=verbose)
            )
            gather_res = await asyncio.gather(enrich_task, trigger_task)
            (intel, enrich_s), (trigger_event, trigger_status, trigger_duration) = gather_res
            result.timings.enrich_s = enrich_s
            result.timings.trigger_s = round(trigger_duration, 2)
            result.trigger_event_status = trigger_status
            if intel:
                intel.trigger_event = trigger_event
        else:
            intel, enrich_s = await enrich_task
            result.timings.enrich_s = enrich_s
            result.timings.trigger_s = 0.0
            result.trigger_event_status = "disabled"
            if intel:
                intel.trigger_event = None

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


async def run_pipeline(
    domains: list[str],
    settings: Settings,
    agentic: bool = False,
    provider: str = "both",
    verbose: bool = False,
) -> list[DomainResult]:
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

        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        active_domains: set[str] = set(clean_domains)

        def _format_active_desc() -> str:
            if not active_domains:
                return "[dim]finalizing...[/dim]"
            domains_list = sorted(active_domains)
            if len(domains_list) > 3:
                joined = f"{domains_list[0]}, {domains_list[1]} +{len(domains_list) - 2} more"
            else:
                joined = ", ".join(domains_list)
            return f"[dim]processing: {joined}[/dim]"

        if not verbose:
            progress = Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("{task.description}"),
                TextColumn("[dim]({task.completed}/{task.total})[/dim]"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            )
            progress.start()
            task_id = progress.add_task(_format_active_desc(), total=len(clean_domains))
        else:
            progress = None
            task_id = None

        async def _bounded(domain: str) -> DomainResult:
            async with semaphore:
                try:
                    res = await asyncio.wait_for(
                        process_domain(
                            domain,
                            settings,
                            browser=browser,
                            agentic=agentic,
                            provider=provider,
                            verbose=verbose,
                        ),
                        timeout=settings.domain_timeout_s,
                    )
                except TimeoutError:
                    res = DomainResult(
                        domain=domain,
                        status=ProcessingStatus.FAILED,
                        error_reason=f"Hard timeout ({settings.domain_timeout_s}s)",
                    )
                except Exception as exc:
                    res = DomainResult(
                        domain=domain,
                        status=ProcessingStatus.FAILED,
                        error_reason=f"Unhandled: {type(exc).__name__}: {str(exc)}",
                    )
                finally:
                    if not verbose and progress is not None and task_id is not None:
                        active_domains.discard(domain)
                        if res.status == ProcessingStatus.SUCCESS:
                            leader = (
                                res.intel.key_team_members[0].name
                                if res.intel and res.intel.key_team_members
                                else ""
                            )
                            leader_str = f" · {leader}" if leader else ""
                            dur = f"{res.timings.total_s:.1f}s"
                            progress.console.print(f"  ok    {domain:<16} ({dur}){leader_str}")
                        elif res.status == ProcessingStatus.PARTIAL:
                            dur = f"{res.timings.total_s:.1f}s"
                            progress.console.print(f"  part  {domain:<16} ({dur})")
                        else:
                            dur = f"{res.timings.total_s:.1f}s"
                            err = res.error_reason[:40]
                            progress.console.print(f"  fail  {domain:<16} ({dur}) · {err}")
                        progress.update(task_id, advance=1, description=_format_active_desc())

                return res

        try:
            results = await asyncio.gather(*[_bounded(d) for d in clean_domains])
        finally:
            if not verbose and progress is not None:
                progress.stop()
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
        help='Comma-separated list of domains, e.g. "notion.com,stripe.com,linear.app"',
    )
    parser.add_argument(
        "--agentic",
        action="store_true",
        help="Enable autonomous Browser-Use agent for trigger event discovery",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose action-by-action logging for debugging agent actions",
    )
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Custom run ID for output files (e.g. --name demo -> run_demo.json)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open generated output files in VS Code after completion",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="auto",
        choices=["auto", "both", "openrouter", "groq"],
        help=(
            'LLM provider for trigger agent: "auto" (interactive prompt), '
            '"both" (OpenRouter + Groq fallback), "openrouter", or "groq"'
        ),
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    configure_logging(verbose=args.verbose)
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]

    if not domains:
        console.print("[dim]error: no domains provided[/dim]")
        return

    settings = load_settings()

    # Resolve LLM provider for trigger agent
    provider = args.provider
    if args.agentic and provider == "auto":
        has_or = bool(settings.openrouter_api_key and settings.openrouter_api_key.strip())
        has_groq = bool(settings.groq_api_key and settings.groq_api_key.strip())

        if has_or and has_groq:
            console.print("[bold]LLM provider for trigger agent:[/bold]")
            console.print("  [cyan][1][/cyan] OpenRouter (gpt-4o-mini) + Groq fallback")
            console.print("  [cyan][2][/cyan] Groq only")
            console.print("  [cyan][3][/cyan] OpenRouter only")
            try:
                choice = input("Pick [1/2/3] (default: 1): ").strip()
            except (EOFError, KeyboardInterrupt):
                choice = ""
            provider_map = {"1": "both", "2": "groq", "3": "openrouter", "": "both"}
            provider = provider_map.get(choice, "both")
        elif has_or:
            provider = "openrouter"
        elif has_groq:
            provider = "groq"
        else:
            provider = "both"  # will gracefully degrade in trigger_agent

        provider_labels = {
            "both": "OpenRouter + Groq fallback",
            "openrouter": "OpenRouter only",
            "groq": "Groq only",
        }
        console.print(f"  [dim]→ using {provider_labels.get(provider, provider)}[/dim]\n")
    elif not args.agentic:
        provider = "both"  # doesn't matter, trigger agent won't run

    mode_str = " · [dim]agentic[/dim]" if args.agentic else ""
    console.print(
        f"\n[bold]lead-enrich[/bold] · {len(domains)} domain(s){mode_str} "
        f"[dim](concurrency={settings.max_concurrent_domains})[/dim]\n"
    )

    start = time.monotonic()

    results = await run_pipeline(
        domains,
        settings,
        agentic=args.agentic,
        provider=provider,
        verbose=args.verbose,
    )

    elapsed = round(time.monotonic() - start, 1)

    if args.name:
        clean_name = "".join(c for c in args.name if c.isalnum() or c in ("-", "_")).strip()
        run_id = clean_name or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    else:
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
    succeeded = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
    partial = sum(1 for r in results if r.status == ProcessingStatus.PARTIAL)
    failed = sum(1 for r in results if r.status == ProcessingStatus.FAILED)

    console.print(
        f"\n[bold]done in {elapsed}s[/bold] · {succeeded} ok, {partial} partial, {failed} failed "
        f"[dim]({run_id})[/dim]"
    )
    console.print(f"  json      {run_json}")
    console.print(f"  csv       {run_csv}")
    console.print(f"  manifest  {manifest_path}")
    console.print(f"  master    {settings.output_dir / 'all_leads.csv'}")

    # Cost report
    print_cost_report(results)

    if args.open:
        try:
            subprocess.run(["code", str(run_json), str(run_csv)], check=False)
            console.print(f"  [dim]opened {run_json.name} and {run_csv.name} in VS Code[/dim]")
        except Exception as exc:
            console.print(f"  [dim]could not launch VS Code: {exc}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
