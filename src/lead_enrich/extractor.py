"""
LLM extraction — sends preprocessed text to Groq via Instructor and gets back
a validated CompanyIntel object.

Uses instructor.from_provider() which handles the Groq client setup and
structured output via tool calling. We don't parse JSON by hand or use regex
on LLM output — that's exactly what Instructor is designed to avoid.
"""

from __future__ import annotations

import asyncio

import instructor
import structlog
from groq import APIStatusError, AsyncGroq, RateLimitError
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from lead_enrich.config import Settings
from lead_enrich.models import CompanyIntel, TeamMember, TokenUsage

log = structlog.get_logger()

# Pricing per million tokens — Groq is currently free, but we track costs
# using OpenAI-equivalent rates to demonstrate the methodology.
COST_PER_1M_INPUT = 0.59  # USD
COST_PER_1M_OUTPUT = 0.79

# Concurrency control for LLM calls — allow 2 parallel requests with gentle spacing
# to prevent exceeding rate limits on free-tier provider endpoints.
_llm_semaphore = asyncio.Semaphore(2)


def _is_retryable_error(exc: BaseException) -> bool:
    """Detect rate-limit or temporary capacity errors across Groq and Instructor."""
    err = str(exc).lower()
    return (
        isinstance(exc, (RateLimitError, APIStatusError))
        or "rate_limit" in err
        or "429" in err
        or "try again" in err
        or "tokens per minute" in err
    )


SYSTEM_PROMPT = (
    "You are a lead intelligence analyst extracting structured data for a target company.\n"
    "CRITICAL RULES:\n"
    "- Extract key founders, C-level executives (CEO, CTO, COO, etc.), VPs, and leadership team members\n"
    "  who work directly for the TARGET company (up to 3-5 leaders). Include their full name and exact role.\n"
    "- NEVER extract customer testimonials, partner quotes, investors, advisors, or customer logos as team members.\n"
    "- If no founders or leadership are explicitly named in the text, leave key_team_members as [].\n"
    "- For each team member, populate 'name' with their full human name and 'role' with their executive title.\n"
    "- Company overview: 1-2 concise sentences of what they do and why notable.\n"
    "- Target audience: primary customer/user segments."
)


class _LLMCompanyIntel(BaseModel):
    """Extraction target for Instructor to avoid floating-point syntax quirks across models."""

    company_overview: str = Field(
        "", description="Concise 1-2 sentence summary of what the company does and why notable."
    )
    target_audience: str = Field("", description="Primary target customer and user personas.")
    contact_emails: list[str] = Field(
        default_factory=list, description="Generic contact emails found on the page."
    )
    key_team_members: list[TeamMember] = Field(
        default_factory=list,
        description="Top 3-5 key founders, C-level executives, and leadership team members.",
    )


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.5, min=4, max=20),
    retry=retry_if_exception(_is_retryable_error),
    before_sleep=lambda rs: log.warning(
        "llm_retry", attempt=rs.attempt_number, wait=rs.next_action.sleep
    ),
)
async def _call_llm(
    client: instructor.Instructor,
    model: str,
    text: str,
    domain: str,
    max_tokens: int = 650,
) -> tuple[CompanyIntel, any]:
    """Execute Instructor completion under retry policy with bounded output tokens."""
    raw_intel, completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Company: {domain}\n\nWebsite content:\n{text}",
            },
        ],
        response_model=_LLMCompanyIntel,
        # 650 tokens allows complete JSON structure without truncation
        max_tokens=max_tokens,
    )
    intel = CompanyIntel(
        company_overview=raw_intel.company_overview,
        target_audience=raw_intel.target_audience,
        contact_emails=raw_intel.contact_emails,
        key_team_members=raw_intel.key_team_members,
        confidence_score=0.8,
    )
    return intel, completion


async def extract_company_intel(
    text: str, domain: str, settings: Settings
) -> tuple[CompanyIntel, TokenUsage]:
    """
    Send preprocessed content to the LLM and get structured output back.

    Returns both the extracted intel and token usage stats for cost tracking.
    Paces requests across a 2-task semaphore to avoid hitting rolling TPM windows.
    """
    groq_client = AsyncGroq(api_key=settings.groq_api_key)
    client = instructor.from_groq(groq_client, mode=instructor.Mode.TOOLS)

    async with _llm_semaphore:
        await asyncio.sleep(0.25)  # Micro-pacing prevents concurrent burst collisions
        try:
            intel, completion = await _call_llm(client, settings.llm_model, text, domain)
        except Exception as exc:
            err_msg = str(exc).lower()
            if "tokens per day" in err_msg or "tpd" in err_msg or "daily" in err_msg:
                fallback_model = (
                    "openai/gpt-oss-20b"
                    if settings.llm_model != "openai/gpt-oss-20b"
                    else "qwen/qwen3.6-27b"
                )
                log.warning("model_quota_fallback", domain=domain, fallback=fallback_model)
                intel, completion = await _call_llm(client, fallback_model, text, domain)
            elif "parse tool call" in err_msg or "tool_use_failed" in err_msg or "400" in err_msg:
                log.warning("tool_parse_fallback_json", domain=domain)
                json_client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
                await asyncio.sleep(0.4)
                intel, completion = await _call_llm(
                    json_client, settings.llm_model, text, domain, max_tokens=700
                )
            elif "too large" in err_msg or "rate_limit" in err_msg or "413" in err_msg:
                log.warning("llm_tokens_exceeded_fallback", domain=domain, original_len=len(text))
                truncated_text = text[: int(len(text) * 0.55)]
                await asyncio.sleep(0.8)
                intel, completion = await _call_llm(
                    client, settings.llm_model, truncated_text, domain
                )
            else:
                raise

    # Pull token counts from the raw completion
    usage = completion.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total = prompt_tokens + completion_tokens

    token_usage = TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        estimated_cost_usd=round(
            (prompt_tokens / 1_000_000) * COST_PER_1M_INPUT
            + (completion_tokens / 1_000_000) * COST_PER_1M_OUTPUT,
            6,
        ),
    )

    log.info(
        "extraction_complete",
        domain=domain,
        tokens=total,
        confidence=intel.confidence_score,
    )
    return intel, token_usage
