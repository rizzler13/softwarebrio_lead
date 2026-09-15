"""
Tests for rate limiting and provider routing.

Verifies:
1. TokenBucket sliding window behavior
2. ProviderRouter failover logic
3. Provider health tracking (consecutive failures, cooldown)
4. Best provider selection based on capacity
"""

from __future__ import annotations

import time

from lead_enrich.rate_limiter import ProviderRouter, ProviderState, TokenBucket


class TestTokenBucket:
    """Test sliding-window TPM tracker."""

    def test_initial_state(self):
        bucket = TokenBucket(tpm_limit=10_000)
        assert bucket.consumed == 0
        assert bucket.remaining == 10_000

    def test_record_consumption(self):
        bucket = TokenBucket(tpm_limit=10_000)
        bucket.record(3000)
        assert bucket.consumed == 3000
        assert bucket.remaining == 7000

    def test_can_consume_within_limit(self):
        bucket = TokenBucket(tpm_limit=10_000)
        bucket.record(8000)
        assert bucket.can_consume(2000)
        assert not bucket.can_consume(3000)

    def test_window_expiry(self):
        bucket = TokenBucket(tpm_limit=10_000, window_seconds=0.1)
        bucket.record(9000)
        assert bucket.remaining == 1000
        # Wait for window to expire
        time.sleep(0.15)
        assert bucket.remaining == 10_000

    def test_multiple_records(self):
        bucket = TokenBucket(tpm_limit=10_000)
        bucket.record(2000)
        bucket.record(3000)
        bucket.record(1000)
        assert bucket.consumed == 6000
        assert bucket.remaining == 4000


class TestProviderState:
    """Test provider health tracking."""

    def test_record_success_resets_failures(self):
        state = ProviderState(
            name="test",
            bucket=TokenBucket(tpm_limit=10_000),
            consecutive_failures=2,
        )
        state.record_success(1000)
        assert state.consecutive_failures == 0
        assert state.bucket.consumed == 1000

    def test_record_failure_disables_after_threshold(self):
        state = ProviderState(
            name="test",
            bucket=TokenBucket(tpm_limit=10_000),
        )
        state.record_failure()
        state.record_failure()
        assert state.is_available
        state.record_failure()  # 3rd failure
        assert not state.is_available

    def test_cooldown_re_enables(self):
        state = ProviderState(
            name="test",
            bucket=TokenBucket(tpm_limit=10_000),
        )
        state._COOLDOWN_S = 0.1  # Short cooldown for testing
        # Disable provider
        for _ in range(3):
            state.record_failure()
        assert not state.is_available
        # Wait for cooldown
        time.sleep(0.15)
        state.check_cooldown()
        assert state.is_available
        assert state.consecutive_failures == 0


class TestProviderRouter:
    """Test intelligent provider routing."""

    def _make_router(self, groq_tpm=30_000, openrouter_tpm=200_000):
        router = ProviderRouter()
        router.configure(
            groq_tpm=groq_tpm,
            openrouter_tpm=openrouter_tpm,
            has_groq_key=True,
            has_openrouter_key=True,
        )
        return router

    def test_both_available_prefers_openrouter(self):
        router = self._make_router()
        provider = router.get_best_provider(estimated_tokens=5000, preferred="both")
        assert provider == "openrouter"

    def test_groq_preferred(self):
        router = self._make_router()
        provider = router.get_best_provider(estimated_tokens=5000, preferred="groq")
        assert provider == "groq"

    def test_openrouter_preferred(self):
        router = self._make_router()
        provider = router.get_best_provider(estimated_tokens=5000, preferred="openrouter")
        assert provider == "openrouter"

    def test_failover_when_primary_exhausted(self):
        router = self._make_router(groq_tpm=5000)
        # Exhaust Groq
        router.groq.bucket.record(5000)
        provider = router.get_best_provider(estimated_tokens=3000, preferred="groq")
        # Should failover to openrouter
        assert provider == "openrouter"

    def test_only_groq_key(self):
        router = ProviderRouter()
        router.configure(has_groq_key=True, has_openrouter_key=False)
        provider = router.get_best_provider(preferred="both")
        assert provider == "groq"

    def test_only_openrouter_key(self):
        router = ProviderRouter()
        router.configure(has_groq_key=False, has_openrouter_key=True)
        provider = router.get_best_provider(preferred="both")
        assert provider == "openrouter"

    def test_no_keys_returns_none(self):
        router = ProviderRouter()
        router.configure(has_groq_key=False, has_openrouter_key=False)
        provider = router.get_best_provider(preferred="both")
        assert provider is None

    def test_record_success(self):
        router = self._make_router()
        router.record_success("groq", 5000)
        assert router.groq.bucket.consumed == 5000
        assert router.groq.consecutive_failures == 0

    def test_record_failure(self):
        router = self._make_router()
        router.record_failure("groq")
        assert router.groq.consecutive_failures == 1

    def test_get_status(self):
        router = self._make_router()
        status = router.get_status()
        assert "groq" in status
        assert "openrouter" in status
        assert status["groq"]["available"]
        assert status["openrouter"]["available"]
