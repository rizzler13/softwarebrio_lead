"""
Unit tests for Browser-Use agentic trigger event discovery.

Verifies:
1. Timeout degradation (stage returns None, "timeout" without raising)
2. Malformed output handling (gracefully falls back without crashing)
3. Found=False handling (clean TriggerEvent with found=False)
4. External domain hop restriction logic
5. Grounded confidence score calculation (0.3 cap when unconfirmed, 0.7-0.9 on overlap)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lead_enrich.config import Settings
from lead_enrich.trigger_agent import (
    TriggerEventOutput,
    _extract_host,
    _is_external_domain,
    compute_trigger_confidence,
    discover_trigger_event,
)


def _make_test_settings(openrouter_key: str = "mock-key") -> Settings:
    return Settings(
        groq_api_key="mock-groq-key",
        openrouter_api_key=openrouter_key,
        trigger_stage_timeout_s=1.0,
        trigger_max_steps=4,
    )


class TestDomainHopLogic:
    """Test the external domain hop tracking and boundary logic."""

    def test_extract_host(self):
        assert _extract_host("https://www.notion.com/about") == "notion.com"
        assert _extract_host("http://linear.app:8080/blog") == "linear.app"
        assert _extract_host("sub.stripe.com") == "sub.stripe.com"

    def test_is_external_domain(self):
        assert not _is_external_domain("https://notion.com/blog", "notion.com")
        assert not _is_external_domain("https://blog.notion.com/post", "notion.com")
        assert not _is_external_domain("https://www.notion.com/news", "notion.com")
        assert _is_external_domain("https://techcrunch.com/article", "notion.com")
        assert _is_external_domain("https://twitter.com/notionhq", "notion.com")


class TestTriggerConfidenceScorer:
    """Test grounded confidence scoring without agent self-assessment."""

    def test_empty_or_not_found(self):
        item = TriggerEventOutput(found=False)
        assert compute_trigger_confidence(item, ["https://example.com"]) == 0.0

    def test_unreachable_source_capped_at_0_3(self):
        item = TriggerEventOutput(
            found=True,
            summary="Raised Series B funding of $50M from Sequoia.",
            source_url="https://techcrunch.com/funding-announcement",
            estimated_date="2026-05",
        )
        # Visited URLs does not contain the source URL
        score = compute_trigger_confidence(
            item, ["https://example.com/about", "https://example.com/team"]
        )
        assert score == 0.30

    def test_visited_source_with_keyword_overlap(self):
        item = TriggerEventOutput(
            found=True,
            summary="Raised Series B funding of $50M from Sequoia Capital.",
            source_url="https://example.com/blog/series-b",
            estimated_date="May 2026",
        )
        visited = ["https://example.com", "https://example.com/blog/series-b"]
        extracted_text = (
            "We are thrilled to announce our Series B funding round led by Sequoia Capital."
        )
        score = compute_trigger_confidence(item, visited, extracted_text, base_domain="example.com")
        assert score >= 0.80

    def test_bare_homepage_citation_capped_at_0_3(self):
        """Bare homepage citing a specific funding round must be hard-capped at <= 0.30."""
        item = TriggerEventOutput(
            found=True,
            summary="Clerk raises $50m Series C",
            source_url="https://clerk.com/",
            estimated_date="2026-09-13",
        )
        visited = ["https://clerk.com/"]
        extracted_text = "Clerk authentication and user management platform for React and Next.js"
        score = compute_trigger_confidence(item, visited, extracted_text, base_domain="clerk.com")
        assert score <= 0.30

    def test_uncorroborated_text_capped_at_0_3(self):
        """Visited URL whose text does not mention the claimed event must be capped at <= 0.30."""
        item = TriggerEventOutput(
            found=True,
            summary="Acquired Acme Corp for $100M in cash",
            source_url="https://example.com/news/article",
            estimated_date="2026-01",
        )
        visited = ["https://example.com/news/article"]
        extracted_text = "Our winter release introduces new dark mode and faster dashboard filters."
        score = compute_trigger_confidence(item, visited, extracted_text, base_domain="example.com")
        assert score <= 0.30

    def test_substring_word_boundary_does_not_false_match(self):
        """Page words like 'fundamental' or 'prevention' must not match 'fund' or 'event'."""
        item = TriggerEventOutput(
            found=True,
            summary="Raised Series C funding round",
            source_url="https://example.com/news/article",
            estimated_date="2026-01",
        )
        visited = ["https://example.com/news/article"]
        # Words contain substrings of summary keywords ('fund' in fundamental, 'seri' in serialize)
        extracted_text = "Fundamental serialization improvements across our platform services."
        score = compute_trigger_confidence(item, visited, extracted_text, base_domain="example.com")
        assert score <= 0.30


class TestTriggerAgentDegradation:
    """Test that agent failures degrade cleanly and never crash the pipeline."""

    @pytest.mark.asyncio
    async def test_skipped_when_no_api_key(self):
        settings = _make_test_settings(openrouter_key="")
        event, status, duration = await discover_trigger_event("notion.com", settings)
        assert event is None
        assert status == "skipped"
        assert duration == 0.0

    @pytest.mark.asyncio
    async def test_timeout_degrades_cleanly(self):
        settings = _make_test_settings()
        settings.trigger_stage_timeout_s = 0.05

        async def _slow_agent(*args, **kwargs):
            await asyncio.sleep(0.5)
            return None, "completed"

        with patch("lead_enrich.trigger_agent._run_browser_use_agent", side_effect=_slow_agent):
            event, status, duration = await discover_trigger_event("notion.com", settings)
            assert event is None
            assert status == "timeout"
            assert duration >= 0.05

    @pytest.mark.asyncio
    async def test_agent_error_degrades_cleanly(self):
        settings = _make_test_settings()

        async def _crash_agent(*args, **kwargs):
            raise RuntimeError("Browser session crashed unexpectedly")

        with patch("lead_enrich.trigger_agent._run_browser_use_agent", side_effect=_crash_agent):
            event, status, duration = await discover_trigger_event("notion.com", settings)
            assert event is None
            assert status == "error"

    @pytest.mark.asyncio
    async def test_found_false_returns_clean_event(self):
        settings = _make_test_settings()

        mock_output = TriggerEventOutput(found=False)
        mock_history = MagicMock()
        mock_history.get_structured_output.return_value = mock_output
        mock_history.urls.return_value = ["https://notion.com"]
        mock_history.extracted_content.return_value = ["Welcome to Notion"]

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_history)

        with (
            patch("browser_use.Agent", return_value=mock_agent),
            patch("browser_use.BrowserSession") as mock_session,
            patch("browser_use.llm.ChatOpenRouter"),
        ):
            mock_session.return_value.close = AsyncMock()
            event, status, duration = await discover_trigger_event("notion.com", settings)
            assert event is not None
            assert event.found is False
            assert event.event_type is None
            assert status == "completed"
