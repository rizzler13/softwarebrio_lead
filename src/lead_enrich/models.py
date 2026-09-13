"""
Pydantic models for the entire pipeline.

These are the contracts between stages — browser output, LLM extraction target,
and final output format all defined here so nothing drifts.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

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


# ---------------------------------------------------------------------------
# LLM extraction target — this is what Instructor fills in
# ---------------------------------------------------------------------------


class TeamMember(BaseModel):
    """A person found on the company's public pages."""

    name: str
    role: str = ""
    linkedin_url: str | None = None


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
    total_s: float = 0.0


class DomainResult(BaseModel):
    """One row in the final output — every domain gets one, even if it failed."""

    domain: str
    status: ProcessingStatus = ProcessingStatus.FAILED
    error_reason: str = ""
    intel: CompanyIntel | None = None
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
