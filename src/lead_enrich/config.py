"""
Configuration loaded from environment variables and .env file.

Keeps all tunables in one place so nothing is hardcoded across modules.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    tavily_api_key: str = ""  # optional — enrichment degrades gracefully without it

    # Model (qwen/qwen3.8-27b is currently active on Groq with native tool-use support)
    llm_model: str = "qwen/qwen3.8-27b"

    # Concurrency & timeouts
    max_concurrent_domains: int = 10
    page_timeout_ms: int = 10_000  # 10s per page with asset blocking to prevent false timeouts
    domain_timeout_s: int = 40  # 40s hard ceiling per domain (allows multi-domain batch queuing)
    request_delay_s: tuple[float, float] = (0.1, 0.3)  # polite delay between page requests

    # Content processing: 950 tokens captures homepage pitch, audience, and leadership
    # while keeping prompt token payload compact and avoiding Groq's 7,000 ITPM rate limit.
    token_budget: int = 950

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
