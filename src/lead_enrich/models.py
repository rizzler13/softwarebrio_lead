"""
Pydantic models for the entire pipeline.

These are the contracts between stages — browser output, LLM extraction target,
and final output format all defined here so nothing drifts.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Internal data passed between pipeline stages
# ---------------------------------------------------------------------------


class PageContent(BaseModel):
    """What we got back from fetching a single page."""

    url: str
    text: str = ""
    emails: list[str] = Field(default_factory=list)
    meta_description: str = ""
    status_code: int = 200
    error: str = ""


class TeamMember(BaseModel):
    """A person found on the company's public pages."""

    name: str = Field("", description="Full name of the executive or founder.")
    full_name: str | None = Field(None, description="Optional full name field.", exclude=True)
    role: str = Field("", description="Job title or executive role.")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL.")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @model_validator(mode="before")
    @classmethod
    def _accept_full_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("name") and data.get("full_name"):
                data["name"] = data["full_name"]
        return data


# ---------------------------------------------------------------------------
# Agentic Trigger Event model
# ---------------------------------------------------------------------------


class TriggerEvent(BaseModel):
    """Recent company trigger event discovered by the agentic trigger stages."""

    found: bool = False
    event_type: Literal["funding", "leadership_change", "product_news", "other"] | None = None
    summary: str | None = None  # 1-2 sentences in the agent's own words
    source_url: str | None = None  # the page where it was found/confirmed
    estimated_date: str | None = None  # month/year or date string
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    trigger_phase: Literal["http", "agent", "cached", "skipped"] | None = None


# ---------------------------------------------------------------------------
# LLM extraction target — this is what Instructor fills in
# ---------------------------------------------------------------------------


class CompanyIntel(BaseModel):
    """Structured intelligence extracted from a company's web presence.

    Instructor maps LLM output directly onto this schema, so field names
    and descriptions double as prompt guidance.
    """

    company_overview: str = Field(
        "",
        description="Concise 1-2 sentence summary of product and notable traits.",
    )
    target_audience: str = Field(
        "",
        description="Primary target customers/audience.",
    )
    contact_emails: list[str] = Field(
        default_factory=list,
        description="Public generic contact emails.",
    )
    key_team_members: list[TeamMember] = Field(
        default_factory=list,
        description="Top 2-3 key founders or C-level executives only.",
    )
    confidence_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0.",
    )
    trigger_event: TriggerEvent | None = None


# ---------------------------------------------------------------------------
# Final output — wraps CompanyIntel with metadata
# ---------------------------------------------------------------------------


class ProcessingStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class TokenUsage(BaseModel):
    """Tracks how many tokens the LLM consumed for cost reporting."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class StageTimings(BaseModel):
    """Latency breakdown per processing stage in seconds."""

    fetch_s: float = 0.0
    preprocess_s: float = 0.0
    llm_s: float = 0.0
    enrich_s: float = 0.0
    trigger_s: float = 0.0
    trigger_http_s: float = 0.0  # Phase 1 HTTP-only trigger discovery
    total_s: float = 0.0


class DomainResult(BaseModel):
    """One row in the final output — every domain gets one, even if it failed."""

    domain: str
    status: ProcessingStatus = ProcessingStatus.FAILED
    error_reason: str = ""
    intel: CompanyIntel | None = None
    trigger_event_status: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    timings: StageTimings = Field(default_factory=StageTimings)
    processing_time_s: float = 0.0
    pages_fetched: int = 0
    urls_discovered: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Error information for a domain that failed or had partial extraction."""

    domain: str
    error_reason: str


class RunManifest(BaseModel):
    """Telemetry manifest generated for each pipeline run."""

    # Run identity
    run_id: str
    git_commit_hash: str = "uncommitted"
    model_used: str

    # Input
    domains_requested: int
    domains: list[str]

    # Results breakdown
    success_count: int
    partial_count: int
    failed_count: int
    errors: list[ErrorDetail] = Field(default_factory=list)

    # Timing
    total_duration_seconds: float
    per_domain_duration: dict[str, float] = Field(default_factory=dict)

    # Cost / usage
    avg_tokens_per_domain: float
    total_tokens: int
    total_cost_usd: float

    # Quality
    avg_confidence_score: float

    # Agentic stage telemetry
    trigger_events_found: int = 0
    trigger_http_hits: int = 0  # events found by Phase 1 (zero LLM tokens)
    trigger_agent_hits: int = 0  # events found by Phase 2 (browser-use agent)
    trigger_cache_hits: int = 0  # events served from cache
    avg_trigger_stage_duration_s: float = 0.0
    trigger_stage_timeouts: int = 0
