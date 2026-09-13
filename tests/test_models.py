"""Tests for Pydantic models — make sure our schemas validate correctly."""

import pytest
from pydantic import ValidationError

from lead_enrich.models import (
    CompanyIntel,
    DomainResult,
    PageContent,
    ProcessingStatus,
    TeamMember,
    TokenUsage,
)


class TestTeamMember:
    def test_basic_creation(self):
        member = TeamMember(name="Jane Smith", role="CEO")
        assert member.name == "Jane Smith"
        assert member.role == "CEO"
        assert member.linkedin_url is None

    def test_with_linkedin(self):
        member = TeamMember(
            name="John Doe",
            role="CTO",
            linkedin_url="https://linkedin.com/in/johndoe",
        )
        assert member.linkedin_url == "https://linkedin.com/in/johndoe"


class TestCompanyIntel:
    def test_empty_is_valid(self):
        """All fields have defaults, so an empty CompanyIntel should be fine."""
        intel = CompanyIntel()
        assert intel.company_overview == ""
        assert intel.confidence_score == 0.0

    def test_confidence_score_bounds(self):
        """Score must be between 0.0 and 1.0."""
        intel = CompanyIntel(confidence_score=0.85)
        assert intel.confidence_score == 0.85

        with pytest.raises(ValidationError):
            CompanyIntel(confidence_score=1.5)

        with pytest.raises(ValidationError):
            CompanyIntel(confidence_score=-0.1)

    def test_full_population(self):
        intel = CompanyIntel(
            company_overview="Acme makes widgets. They're the best at it.",
            target_audience="Enterprise manufacturing teams",
            contact_emails=["contact@acme.com", "sales@acme.com"],
            key_team_members=[
                TeamMember(name="Jane", role="CEO"),
                TeamMember(name="Bob", role="CTO", linkedin_url="https://linkedin.com/in/bob"),
            ],
            confidence_score=0.9,
        )
        assert len(intel.key_team_members) == 2
        assert len(intel.contact_emails) == 2


class TestDomainResult:
    def test_failed_domain_still_has_structure(self):
        """A failed domain should still produce a valid record with status and reason."""
        result = DomainResult(
            domain="broken-site.com",
            status=ProcessingStatus.FAILED,
            error_reason="Connection refused",
        )
        assert result.domain == "broken-site.com"
        assert result.status == ProcessingStatus.FAILED
        assert result.intel is None
        assert result.token_usage.total_tokens == 0

    def test_successful_domain(self):
        result = DomainResult(
            domain="example.com",
            status=ProcessingStatus.SUCCESS,
            intel=CompanyIntel(company_overview="Example does stuff."),
            processing_time_s=5.3,
            pages_fetched=4,
        )
        assert result.status == ProcessingStatus.SUCCESS
        assert result.intel is not None

    def test_serialization_roundtrip(self):
        """Make sure we can serialize to JSON and back without losing data."""
        result = DomainResult(
            domain="test.com",
            status=ProcessingStatus.PARTIAL,
            intel=CompanyIntel(
                company_overview="Test company.",
                key_team_members=[TeamMember(name="Alice", role="Founder")],
            ),
            token_usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        data = result.model_dump(mode="json")
        restored = DomainResult(**data)
        assert restored.domain == "test.com"
        assert restored.intel.key_team_members[0].name == "Alice"


class TestPageContent:
    def test_defaults(self):
        page = PageContent(url="https://example.com")
        assert page.text == ""
        assert page.emails == []
        assert page.error == ""
