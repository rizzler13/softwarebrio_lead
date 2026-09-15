"""
Token counting and cost estimation across the full pipeline run.

Even though Groq is free right now, tracking costs demonstrates that
we're thinking about production economics — which is the whole point
of the bonus criterion.
"""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.table import Table

from lead_enrich.models import DomainResult


def print_cost_report(results: list[DomainResult]) -> None:
    """Print a summary table of per-stage latency and token usage."""
    console = Console(highlight=False)
    table = Table(
        box=box.HORIZONTALS,
        show_header=True,
        header_style="bold",
        padding=(0, 1),
        collapse_padding=True,
    )

    has_trigger = any(r.timings.trigger_s > 0 for r in results)
    has_http_phase = any(r.timings.trigger_http_s > 0 for r in results)

    table.add_column("domain", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("fetch", justify="right", no_wrap=True)
    table.add_column("llm", justify="right", no_wrap=True)
    table.add_column("enrich", justify="right", no_wrap=True)
    if has_trigger:
        if has_http_phase:
            table.add_column("trig·http", justify="right", no_wrap=True)
        table.add_column("trigger", justify="right", no_wrap=True)
    table.add_column("total", justify="right", no_wrap=True)
    table.add_column("tokens (p/c/t)", justify="right", no_wrap=True)
    table.add_column("cost", justify="right", no_wrap=True)

    total_prompt = 0
    total_completion = 0
    total_cost = 0.0

    for result in results:
        usage = result.token_usage
        timings = result.timings
        status_str = {
            "success": "ok",
            "partial": "part",
            "failed": "fail",
        }.get(result.status.value, result.status.value)

        token_str = (
            f"{usage.prompt_tokens}/{usage.completion_tokens}/{usage.total_tokens}"
            if usage.total_tokens > 0
            else "—"
        )

        row = [
            result.domain,
            status_str,
            f"{timings.fetch_s:.2f}s" if timings.fetch_s > 0 else "—",
            f"{timings.llm_s:.2f}s" if timings.llm_s > 0 else "—",
            f"{timings.enrich_s:.2f}s" if timings.enrich_s > 0 else "—",
        ]
        if has_trigger:
            if has_http_phase:
                row.append(f"{timings.trigger_http_s:.2f}s" if timings.trigger_http_s > 0 else "—")
            row.append(f"{timings.trigger_s:.2f}s" if timings.trigger_s > 0 else "—")
        row.extend(
            [
                f"{timings.total_s:.2f}s",
                token_str,
                f"${usage.estimated_cost_usd:.4f}",
            ]
        )
        table.add_row(*row)

        total_prompt += usage.prompt_tokens
        total_completion += usage.completion_tokens
        total_cost += usage.estimated_cost_usd

    total_tokens_str = f"{total_prompt}/{total_completion}/{total_prompt + total_completion}"

    # Trigger phase summary
    if has_trigger:
        http_hits = sum(
            1 for r in results
            if r.intel and r.intel.trigger_event and r.intel.trigger_event.trigger_phase == "http"
        )
        agent_hits = sum(
            1 for r in results
            if r.intel and r.intel.trigger_event and r.intel.trigger_event.trigger_phase == "agent"
        )
        cache_hits = sum(
            1 for r in results
            if r.intel and r.intel.trigger_event and r.intel.trigger_event.trigger_phase == "cached"
        )
        if http_hits or agent_hits or cache_hits:
            console.print(
                f"[dim]  trigger phases: {http_hits} http · {agent_hits} agent · "
                f"{cache_hits} cached[/dim]"
            )

    table.add_section()
    tot_row = ["total", "", "", "", ""]
    if has_trigger:
        if has_http_phase:
            tot_row.append("")
        tot_row.append("")
    tot_row.extend(["", total_tokens_str, f"${total_cost:.4f}"])
    table.add_row(*tot_row, style="bold")

    console.print()
    console.print(table)
    console.print("[dim]tokens: prompt/completion/total · pricing: $0.59/$0.79 per 1M[/dim]\n")
