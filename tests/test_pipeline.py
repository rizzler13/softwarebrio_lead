"""
End-to-end pipeline tests with mocked failures.

These prove the grading criterion: "the script must never crash midway
when one site fails." We mock specific failure modes and assert that
the pipeline produces DomainResult records with proper error information.
"""

import asyncio
from unittest.mock import patch

import pytest

from lead_enrich.config import Settings
from lead_enrich.main import parse_args, process_domain, run_pipeline
from lead_enrich.models import DomainResult, ProcessingStatus


def _make_settings(**overrides) -> Settings:
    """Create settings with test defaults. Skips .env to avoid side effects."""
    defaults = {
        "groq_api_key": "test-key",
        "tavily_api_key": "",
        "domain_timeout_s": 10,
        "page_timeout_ms": 5000,
        "token_budget": 2000,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


class TestProcessDomainResilience:
    """Each test simulates a different failure mode and checks we get
    a DomainResult back instead of an exception."""

    @pytest.mark.asyncio
    async def test_timeout_produces_failed_result(self):
        """If a domain exceeds its timeout, we should get status=failed, not a crash."""
        settings = _make_settings(domain_timeout_s=2)

        # Mock discover_urls to hang forever
        async def _hang(*args, **kwargs):
            await asyncio.sleep(999)
            return []

        with patch("lead_enrich.main.discover_urls", side_effect=_hang):
            # Use run_pipeline because that's where the timeout wrapping lives
            results = await run_pipeline(["slow-site.com"], settings)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, DomainResult)
        assert result.domain == "slow-site.com"
        assert result.status == ProcessingStatus.FAILED

    @pytest.mark.asyncio
    async def test_browser_crash_produces_failed_result(self):
        """If Playwright throws, we should catch it and produce a result."""
        settings = _make_settings()

        with patch(
            "lead_enrich.main.discover_urls",
            side_effect=RuntimeError("Browser crashed"),
        ):
            result = await process_domain("crashy-site.com", settings)

        assert isinstance(result, DomainResult)
        assert result.status == ProcessingStatus.FAILED
        assert "Browser crashed" in result.error_reason

    @pytest.mark.asyncio
    async def test_empty_pages_produce_failed_result(self):
        """If all pages come back empty, we should fail gracefully."""
        settings = _make_settings()

        with patch("lead_enrich.main.discover_urls", return_value=["https://empty.com"]):
            with patch("lead_enrich.main.fetch_all_pages", return_value=[]):
                result = await process_domain("empty.com", settings)

        assert isinstance(result, DomainResult)
        assert result.status == ProcessingStatus.FAILED


class TestPipelineIsolation:
    """Verify that one domain failing doesn't kill the others."""

    @pytest.mark.asyncio
    async def test_one_failure_doesnt_kill_batch(self):
        """If domain A crashes, domains B and C should still produce results."""
        settings = _make_settings(domain_timeout_s=5)

        call_count = 0

        async def _mock_process(domain, settings, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if domain == "bad-domain.com":
                raise RuntimeError("Simulated crash")
            return DomainResult(
                domain=domain,
                status=ProcessingStatus.SUCCESS,
            )

        with patch("lead_enrich.main.process_domain", side_effect=_mock_process):
            results = await run_pipeline(
                ["good1.com", "bad-domain.com", "good2.com"],
                settings,
            )

        assert len(results) == 3
        # The two good domains should succeed
        statuses = {r.domain: r.status for r in results}
        assert statuses["good1.com"] == ProcessingStatus.SUCCESS
        assert statuses["good2.com"] == ProcessingStatus.SUCCESS
        # The bad domain should be failed, not missing
        assert statuses["bad-domain.com"] == ProcessingStatus.FAILED


class TestCLIArgs:
    """Verify CLI argument parsing handles custom run names and flags."""

    def test_default_args(self):
        with patch("sys.argv", ["lead_enrich", "--domains", "linear.app,railway.app"]):
            args = parse_args()
            assert args.domains == "linear.app,railway.app"
            assert args.name is None
            assert args.open is False

    def test_custom_name_and_open_flags(self):
        with patch(
            "sys.argv",
            ["lead_enrich", "--domains", "linear.app", "--name", "demo_run", "--open"],
        ):
            args = parse_args()
            assert args.domains == "linear.app"
            assert args.name == "demo_run"
            assert args.open is True
