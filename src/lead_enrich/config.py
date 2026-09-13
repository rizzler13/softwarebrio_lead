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
    max_concurrent_domains: int = 5  # Pipelined domain batching prevents queue starvation
    page_timeout_ms: int = 8_000  # 8s per page with asset blocking to prevent false timeouts
    domain_timeout_s: int = 45  # 45s hard ceiling per domain once scheduled
    request_delay_s: tuple[float, float] = (0.1, 0.3)  # polite delay between page requests

    # Content processing: 220 tokens strictly bounds prompt payload to avoid rate limits
    token_budget: int = 220

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
