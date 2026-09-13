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

    # Concurrency & timeouts
    max_concurrent_domains: int = 5  # Pipelined domain batching prevents queue starvation
    page_timeout_ms: int = 8_000  # 8s per page with asset blocking to prevent false timeouts
    domain_timeout_s: int = 70  # 70s ceiling allows 45s trigger stage + fetch/llm stages
    request_delay_s: tuple[float, float] = (0.1, 0.3)  # polite delay between page requests

    # Trigger event agent (Browser-Use)
    trigger_stage_timeout_s: float = 45.0  # hard wall-clock timeout for trigger stage
    trigger_max_steps: int = 8  # max actions allowed per domain

    # Content processing: 320 tokens splits cleanly between homepage pitch and team page
    token_budget: int = 320

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
