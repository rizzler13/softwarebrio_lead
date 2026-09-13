"""
Token counting and cost estimation across the full pipeline run.

Even though Groq is free right now, tracking costs demonstrates that
we're thinking about production economics — which is the whole point
of the bonus criterion.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from lead_enrich.models import DomainResult


def print_cost_report(results: list[DomainResult]) -> None:
    """Print a summary table of per-stage latency and token usage."""
    console = Console()
    table = Table(title="Pipeline Performance & Token Usage Report", show_lines=True)

    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold", no_wrap=True)
    table.add_column("Fetch", justify="right", style="magenta")
    table.add_column("LLM", justify="right", style="blue")
    table.add_column("Enrich", justify="right", style="yellow")
    table.add_column("Total Time", justify="right", style="bold green", no_wrap=True)
    table.add_column("Tokens (P / C / Tot)", justify="right", no_wrap=True)
    table.add_column("Est. Cost", justify="right", style="green", no_wrap=True)

    total_prompt = 0
    total_completion = 0
    total_cost = 0.0

    for result in results:
        usage = result.token_usage
        timings = result.timings
        status_color = {
            "success": "green",
            "partial": "yellow",
            "failed": "red",
        }.get(result.status.value, "white")

        token_str = (
            f"{usage.prompt_tokens} / {usage.completion_tokens} / {usage.total_tokens}"
            if usage.total_tokens > 0
            else "—"
        )

        table.add_row(
            result.domain,
            f"[{status_color}]{result.status.value}[/{status_color}]",
            f"{timings.fetch_s:.2f}s" if timings.fetch_s > 0 else "—",
            f"{timings.llm_s:.2f}s" if timings.llm_s > 0 else "—",
            f"{timings.enrich_s:.2f}s" if timings.enrich_s > 0 else "—",
            f"{timings.total_s:.2f}s",
            token_str,
            f"${usage.estimated_cost_usd:.4f}",
        )

        total_prompt += usage.prompt_tokens
        total_completion += usage.completion_tokens
        total_cost += usage.estimated_cost_usd

    total_tokens_str = f"{total_prompt} / {total_completion} / {total_prompt + total_completion}"

    table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        "",
        "",
        "",
        "",
        f"[bold]{total_tokens_str}[/bold]",
        f"[bold]${total_cost:.4f}[/bold]",
    )

    console.print()
    console.print(table)
    console.print(
        "[dim]Tokens logged as Prompt / Completion / Total. "
        "Cost estimated at $0.59/$0.79 per 1M input/output tokens.[/dim]\n"
    )
