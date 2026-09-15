"""
Centralized rate-limit management and provider routing.

Tracks tokens consumed per provider in a sliding window and provides
intelligent failover between Groq and OpenRouter when one provider
is exhausted. Designed for free-tier limits where every token counts.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field

import structlog

log = structlog.get_logger()


@dataclass
class _WindowEntry:
    """A single token consumption record within the sliding window."""

    tokens: int
    timestamp: float


class TokenBucket:
    """
    Sliding-window token-per-minute (TPM) tracker for a single provider.

    Rather than hard-blocking, this tracker provides visibility into
    remaining capacity and can async-wait for capacity to free up.
    """

    def __init__(self, tpm_limit: int, window_seconds: float = 60.0) -> None:
        self._limit = tpm_limit
        self._window = window_seconds
        self._entries: list[_WindowEntry] = []
        self._lock = asyncio.Lock()

    def _prune(self) -> None:
        """Remove entries outside the sliding window."""
        cutoff = time.monotonic() - self._window
        self._entries = [e for e in self._entries if e.timestamp > cutoff]

    @property
    def consumed(self) -> int:
        """Tokens consumed in the current window."""
        self._prune()
        return sum(e.tokens for e in self._entries)

    @property
    def remaining(self) -> int:
        """Tokens remaining in the current window."""
        return max(0, self._limit - self.consumed)

    def can_consume(self, tokens: int) -> bool:
        """Check if consuming `tokens` would stay within the limit."""
        return self.remaining >= tokens

    def record(self, tokens: int) -> None:
        """Record token consumption (call after a successful LLM request)."""
        self._entries.append(_WindowEntry(tokens=tokens, timestamp=time.monotonic()))

    async def wait_for_capacity(
        self,
        tokens: int,
        backoff_base: float = 2.0,
        backoff_max: float = 30.0,
        max_retries: int = 8,
    ) -> bool:
        """
        Wait until enough capacity is available.

        Returns True if capacity became available, False if max retries exhausted.
        Uses exponential backoff with jitter to avoid thundering herd.
        """
        for attempt in range(max_retries):
            async with self._lock:
                if self.can_consume(tokens):
                    return True

            # Exponential backoff with jitter
            delay = min(backoff_base * (2**attempt), backoff_max)
            jitter = random.uniform(0, delay * 0.3)
            wait_time = delay + jitter

            log.info(
                "rate_limit_waiting",
                attempt=attempt + 1,
                remaining=self.remaining,
                needed=tokens,
                wait_s=round(wait_time, 1),
            )
            await asyncio.sleep(wait_time)

        return False


@dataclass
class ProviderState:
    """Tracks the health and capacity of a single LLM provider."""

    name: str
    bucket: TokenBucket
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    is_available: bool = True

    # After this many consecutive 429s, temporarily disable the provider
    _MAX_CONSECUTIVE_FAILURES: int = 3
    # Re-enable after this cooldown (seconds)
    _COOLDOWN_S: float = 60.0

    def record_success(self, tokens: int) -> None:
        """Record a successful request."""
        self.bucket.record(tokens)
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a rate-limit failure (429)."""
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        if self.consecutive_failures >= self._MAX_CONSECUTIVE_FAILURES:
            self.is_available = False
            log.warning(
                "provider_temporarily_disabled",
                provider=self.name,
                failures=self.consecutive_failures,
                cooldown_s=self._COOLDOWN_S,
            )

    def check_cooldown(self) -> None:
        """Re-enable provider if cooldown has elapsed."""
        if not self.is_available:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self._COOLDOWN_S:
                self.is_available = True
                self.consecutive_failures = 0
                log.info("provider_re_enabled", provider=self.name)


@dataclass
class ProviderRouter:
    """
    Intelligent routing between Groq and OpenRouter based on capacity.

    Free-tier aware — knows the exact TPM limits and routes accordingly.
    Provides auto-failover when the primary provider is exhausted.
    """

    groq: ProviderState = field(default_factory=lambda: ProviderState(
        name="groq",
        bucket=TokenBucket(tpm_limit=30_000),
    ))
    openrouter: ProviderState = field(default_factory=lambda: ProviderState(
        name="openrouter",
        bucket=TokenBucket(tpm_limit=200_000),
    ))

    # Track which providers have API keys configured
    groq_available: bool = False
    openrouter_available: bool = False

    def configure(
        self,
        groq_tpm: int = 30_000,
        openrouter_tpm: int = 200_000,
        has_groq_key: bool = False,
        has_openrouter_key: bool = False,
    ) -> None:
        """Configure provider limits and availability based on API keys."""
        self.groq = ProviderState(name="groq", bucket=TokenBucket(tpm_limit=groq_tpm))
        self.openrouter = ProviderState(
            name="openrouter", bucket=TokenBucket(tpm_limit=openrouter_tpm)
        )
        self.groq_available = has_groq_key
        self.openrouter_available = has_openrouter_key

    def _get_providers_by_preference(self, preferred: str = "both") -> list[ProviderState]:
        """Return providers ordered by preference, filtering unavailable ones."""
        providers = []

        if preferred == "groq":
            if self.groq_available:
                providers.append(self.groq)
            if self.openrouter_available:
                providers.append(self.openrouter)
        elif preferred == "openrouter":
            if self.openrouter_available:
                providers.append(self.openrouter)
            if self.groq_available:
                providers.append(self.groq)
        else:  # "both" — OpenRouter primary (higher TPM), Groq fallback
            if self.openrouter_available:
                providers.append(self.openrouter)
            if self.groq_available:
                providers.append(self.groq)

        return providers

    def get_best_provider(
        self,
        estimated_tokens: int = 5000,
        preferred: str = "both",
    ) -> str | None:
        """
        Select the best available provider for a request.

        Returns the provider name ("groq" or "openrouter") or None if
        all providers are exhausted.
        """
        providers = self._get_providers_by_preference(preferred)

        for provider in providers:
            provider.check_cooldown()
            if provider.is_available and provider.bucket.can_consume(estimated_tokens):
                return provider.name

        # All providers at capacity — return the one with the most remaining capacity
        available = [p for p in providers if p.is_available]
        if available:
            best = max(available, key=lambda p: p.bucket.remaining)
            return best.name

        # All providers disabled — return the first one (will trigger wait)
        if providers:
            return providers[0].name

        return None

    def record_success(self, provider_name: str, tokens: int) -> None:
        """Record a successful LLM call."""
        state = self.groq if provider_name == "groq" else self.openrouter
        state.record_success(tokens)

    def record_failure(self, provider_name: str) -> None:
        """Record a rate-limit failure."""
        state = self.groq if provider_name == "groq" else self.openrouter
        state.record_failure()

    def get_status(self) -> dict:
        """Get a summary of provider status for logging/reporting."""
        return {
            "groq": {
                "available": self.groq_available and self.groq.is_available,
                "remaining_tpm": self.groq.bucket.remaining if self.groq_available else 0,
                "failures": self.groq.consecutive_failures,
            },
            "openrouter": {
                "available": self.openrouter_available and self.openrouter.is_available,
                "remaining_tpm": (
                    self.openrouter.bucket.remaining if self.openrouter_available else 0
                ),
                "failures": self.openrouter.consecutive_failures,
            },
        }
