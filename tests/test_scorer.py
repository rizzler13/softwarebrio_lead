"""Tests for the confidence scoring algorithm."""

from lead_enrich.models import CompanyIntel, TeamMember
from lead_enrich.scorer import compute_confidence


class TestComputeConfidence:
    def test_empty_intel_scores_low(self):
        """Nothing extracted → should score near zero."""
        intel = CompanyIntel()
        score = compute_confidence(intel)
        assert score <= 0.15  # only the LLM's default 0.0 * 0.3

    def test_full_intel_scores_high(self):
        """Everything populated → should score above 0.7."""
        intel = CompanyIntel(
            company_overview="Acme builds tools for developers. They focus on API testing.",
            target_audience="Backend developers building REST APIs",
            contact_emails=["contact@acme.com"],
            key_team_members=[
                TeamMember(name="Jane", role="CEO", linkedin_url="https://linkedin.com/in/jane"),
                TeamMember(name="Bob", role="CTO"),
            ],
            confidence_score=0.9,  # LLM's self-assessment
        )
        score = compute_confidence(intel)
        assert score >= 0.7

    def test_partial_intel_scores_middle(self):
        """Some fields populated → should be in the 0.3-0.6 range."""
        intel = CompanyIntel(
            company_overview="Acme builds developer tools for modern teams.",
            target_audience="Developers building web applications",
            confidence_score=0.5,
        )
        score = compute_confidence(intel)
        assert 0.3 <= score <= 0.65

    def test_score_is_bounded(self):
        """Score must always be between 0.0 and 1.0."""
        # Even with an aggressive LLM self-score
        intel = CompanyIntel(confidence_score=1.0)
        score = compute_confidence(intel)
        assert 0.0 <= score <= 1.0

    def test_linkedin_urls_boost_score(self):
        """Having LinkedIn URLs should increase confidence."""
        without_linkedin = CompanyIntel(
            company_overview="A company that does things for people who need them.",
            key_team_members=[TeamMember(name="Jane", role="CEO")],
            confidence_score=0.5,
        )
        with_linkedin = CompanyIntel(
            company_overview="A company that does things for people who need them.",
            key_team_members=[
                TeamMember(name="Jane", role="CEO", linkedin_url="https://linkedin.com/in/jane"),
            ],
            confidence_score=0.5,
        )
        score_without = compute_confidence(without_linkedin)
        score_with = compute_confidence(with_linkedin)
        assert score_with > score_without
