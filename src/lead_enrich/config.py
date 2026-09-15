"""
Configuration loaded from environment variables and .env file.

Keeps all tunables in one place so nothing is hardcoded across modules.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    tavily_api_key: str = ""  # optional — enrichment degrades gracefully without it
    openrouter_api_key: str = ""  # for agentic Browser-Use trigger stage

    # Model (openai/gpt-oss-120b provides high throughput and reliable structured outputs)
    llm_model: str = "openai/gpt-oss-120b"
    openrouter_model: str = "openai/gpt-4o-mini"
    groq_trigger_model: str = "groq/compound"  # high TPM limit (30k) on Groq for agentic navigation

    # Concurrency & timeouts
    max_concurrent_domains: int = 5  # Pipelined domain batching prevents queue starvation
    page_timeout_ms: int = 8_000  # 8s per page with asset blocking to prevent false timeouts
    domain_timeout_s: int = 80  # 80s ceiling allows 60s trigger stage + fetch/llm stages
    request_delay_s: tuple[float, float] = (0.1, 0.3)  # polite delay between page requests

    # Trigger event agent (Browser-Use)
    trigger_stage_timeout_s: float = 60.0  # 60s ceiling allows multi-step browser navigation
    trigger_max_steps: int = 10  # max actions allowed per domain (enough for blog discovery + read)
    trigger_provider: str = "auto"  # "auto", "both", "openrouter", or "groq"

    # Content processing: 1000 tokens captures homepage pitch, audience, and leadership
    # while keeping prompt token payload compact and well within Groq's TPM limits.
    token_budget: int = 1000

    # Output
    output_dir: Path = Path("output")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # .env may have keys we don't need (github_repo, etc.)
    }


def load_settings() -> Settings:
    """Load and validate settings. Fails fast if GROQ_API_KEY is missing."""
    return Settings()
