"""
Output serialization — writes results to timestamped files, updates the all_leads
master archive, and generates a structured run manifest.
"""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import structlog

from lead_enrich.models import DomainResult, ErrorDetail, ProcessingStatus, RunManifest

log = structlog.get_logger()

CSV_FIELDNAMES = [
    "domain",
    "status",
    "error_reason",
    "company_overview",
    "target_audience",
    "contact_emails",
    "key_team_members",
    "confidence_score",
    "fetch_s",
    "preprocess_s",
    "llm_s",
    "enrich_s",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "processing_time_s",
    "pages_fetched",
]


def _get_git_commit() -> str:
    """Safely get current git commit hash or 'uncommitted'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout.strip() if res.returncode == 0 else "uncommitted"
    except Exception:
        return "uncommitted"


def _format_csv_row(result: DomainResult) -> dict:
    """Convert a DomainResult to a flat CSV dict."""
    intel = result.intel
    team_str = ""
    emails_str = ""

    if intel:
        team_str = "; ".join(
            f"{m.name} ({m.role})" + (f" [{m.linkedin_url}]" if m.linkedin_url else "")
            for m in intel.key_team_members
        )
        emails_str = "; ".join(intel.contact_emails)

    return {
        "domain": result.domain,
        "status": result.status.value,
        "error_reason": result.error_reason,
        "company_overview": intel.company_overview if intel else "",
        "target_audience": intel.target_audience if intel else "",
        "contact_emails": emails_str,
        "key_team_members": team_str,
        "confidence_score": intel.confidence_score if intel else 0.0,
        "fetch_s": result.timings.fetch_s,
        "preprocess_s": result.timings.preprocess_s,
        "llm_s": result.timings.llm_s,
        "enrich_s": result.timings.enrich_s,
        "prompt_tokens": result.token_usage.prompt_tokens,
        "completion_tokens": result.token_usage.completion_tokens,
        "total_tokens": result.token_usage.total_tokens,
        "estimated_cost_usd": result.token_usage.estimated_cost_usd,
        "processing_time_s": round(result.processing_time_s, 2),
        "pages_fetched": result.pages_fetched,
    }


def write_run_output(
    results: list[DomainResult],
    output_dir: Path,
    run_id: str,
    model_name: str,
    total_duration_s: float,
) -> tuple[Path, Path, Path]:
    """
    Write results for this specific run without parsing or rewriting previous records:
    1. output/runs/run_{run_id}.json
    2. output/runs/run_{run_id}.csv
    3. output/runs/manifest_{run_id}.json (telemetry)
    Also appends to the master historical archive output/all_leads.csv and output/all_leads.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write run-specific JSON
    run_json_path = runs_dir / f"run_{run_id}.json"
    run_data = [r.model_dump(mode="json") for r in results]
    run_json_path.write_text(json.dumps(run_data, indent=2, ensure_ascii=False))

    # 2. Write run-specific CSV
    run_csv_path = runs_dir / f"run_{run_id}.csv"
    with open(run_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for r in results:
            writer.writerow(_format_csv_row(r))

    # 3. Create telemetry Manifest
    success_count = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
    partial_count = sum(1 for r in results if r.status == ProcessingStatus.PARTIAL)
    failed_count = sum(1 for r in results if r.status == ProcessingStatus.FAILED)

    errors = [
        ErrorDetail(domain=r.domain, error_reason=r.error_reason)
        for r in results
        if r.status in (ProcessingStatus.PARTIAL, ProcessingStatus.FAILED)
    ]

    total_tokens = sum(r.token_usage.total_tokens for r in results)
    total_cost = sum(r.token_usage.estimated_cost_usd for r in results)
    avg_tokens = round(total_tokens / len(results), 1) if results else 0.0

    scores = [r.intel.confidence_score for r in results if r.intel]
    avg_confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

    per_domain_duration = {r.domain: r.processing_time_s for r in results}

    manifest = RunManifest(
        run_id=run_id,
        git_commit_hash=_get_git_commit(),
        model_used=model_name,
        domains_requested=len(results),
        domains=[r.domain for r in results],
        success_count=success_count,
        partial_count=partial_count,
        failed_count=failed_count,
        errors=errors,
        total_duration_seconds=round(total_duration_s, 2),
        per_domain_duration=per_domain_duration,
        avg_tokens_per_domain=avg_tokens,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 4),
        avg_confidence_score=avg_confidence,
    )

    manifest_path = runs_dir / f"manifest_{run_id}.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json"), indent=2))

    # 4. Maintain all_leads cumulative records
    all_json_path = output_dir / "all_leads.json"
    all_dict: dict[str, dict] = {}
    if all_json_path.exists():
        try:
            prev = json.loads(all_json_path.read_text(encoding="utf-8"))
            if isinstance(prev, list):
                for item in prev:
                    if isinstance(item, dict) and "domain" in item:
                        all_dict[item["domain"]] = item
        except Exception:
            pass
    for r in results:
        all_dict[r.domain] = r.model_dump(mode="json")
    all_json_path.write_text(json.dumps(list(all_dict.values()), indent=2, ensure_ascii=False))

    all_csv_path = output_dir / "all_leads.csv"
    all_csv_rows: dict[str, dict] = {}
    if all_csv_path.exists():
        try:
            with open(all_csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("domain"):
                        all_csv_rows[row["domain"]] = row
        except Exception:
            pass
    for r in results:
        all_csv_rows[r.domain] = _format_csv_row(r)
    with open(all_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in all_csv_rows.values():
            writer.writerow(row)

    log.info(
        "run_output_written",
        run_id=run_id,
        json=str(run_json_path),
        csv=str(run_csv_path),
        manifest=str(manifest_path),
    )
    return run_json_path, run_csv_path, manifest_path


def write_json(results: list[DomainResult], output_dir: Path) -> Path:
    """Legacy compatibility: writes to output/output.json."""
    path = output_dir / "output.json"
    data = [r.model_dump(mode="json") for r in results]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path


def write_csv(results: list[DomainResult], output_dir: Path) -> Path:
    """Legacy compatibility: writes to output/output.csv."""
    path = output_dir / "output.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for r in results:
            writer.writerow(_format_csv_row(r))
    return path
