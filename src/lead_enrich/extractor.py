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
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from lead_enrich.config import Settings
from lead_enrich.models import CompanyIntel, TokenUsage

log = structlog.get_logger()

# Pricing per million tokens — Groq is currently free, but we track costs
# using OpenAI-equivalent rates to demonstrate the methodology.
COST_PER_1M_INPUT = 0.59  # USD
COST_PER_1M_OUTPUT = 0.79

# Concurrency control for LLM calls — allow 3 parallel requests with gentle spacing
# to prevent exceeding rate limits on free-tier provider endpoints.
_llm_semaphore = asyncio.Semaphore(3)


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
    "You are a lead enrichment analyst. Given text extracted from a "
    "company's website, extract structured intelligence.\n\n"
    "Be precise and factual — only include information that's clearly "
    "stated or strongly implied in the text. Don't hallucinate team "
    "members or make up emails.\n\n"
    "For the company overview: write exactly 2 sentences. First sentence "
    "= what the company does. Second sentence = what makes them notable "
    "or different.\n\n"
    "For contact emails: only include emails that look like general/public "
    "addresses (contact@, sales@, support@, hello@, info@). Skip personal "
    "emails and noreply addresses.\n\n"
    "For team members: prioritize the top 3-5 founders and C-level/VP executives. "
    "Do NOT include entire employee rosters or customer testimonial quotes. Only "
    "include a LinkedIn URL if you can see one in the text.\n\n"
    "For confidence score: honestly assess how complete your extraction is. "
    "1.0 means every field is fully populated with high-quality data. "
    "0.5 means you got the basics but missed significant pieces. "
    "Below 0.3 means the page content was too thin to extract much."
)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=20),
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
):
    """Execute Instructor completion under retry policy with bounded output tokens."""
    return await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Extract structured intelligence for the company at {domain}.\n\n"
                    f"Here is the content from their website:\n\n{text}"
                ),
            },
        ],
        response_model=CompanyIntel,
        max_tokens=500,  # Compact budget to ensure rapid response and stay well within rate limits
    )


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
        await asyncio.sleep(0.15)  # Micro-pacing prevents concurrent burst collisions
        try:
            intel, completion = await _call_llm(client, settings.llm_model, text, domain)
        except Exception as exc:
            # If request exceeded token limits, cut text and try one adaptive fallback
            err_msg = str(exc).lower()
            if "too large" in err_msg or "rate_limit" in err_msg or "413" in err_msg:
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
