"""
Confidence scoring — blends deterministic signal checks with the LLM's
own self-assessment.

Pure LLM self-assessment is unreliable (it tends to be overconfident).
Pure signal-based scoring misses nuance (it can't tell if an overview
is actually good, just that one exists). The blend is a pragmatic middle
ground.
"""

from __future__ import annotations

from lead_enrich.models import CompanyIntel


def compute_confidence(intel: CompanyIntel) -> float:
    """
    Compute a blended confidence score from 0.0 to 1.0.

    Weights: 70% signal-based checks, 30% LLM self-assessment.
    """
    signal_score = _check_signals(intel)
    llm_score = intel.confidence_score  # the LLM's own guess

    blended = 0.7 * signal_score + 0.3 * llm_score
    return round(max(0.0, min(1.0, blended)), 2)


def _check_signals(intel: CompanyIntel) -> float:
    """
    Tally up what we actually got vs. what a complete extraction looks like.

    Each signal has a weight reflecting how important it is for lead enrichment.
    """
    score = 0.0

    # Did we get a company overview?
    if intel.company_overview and len(intel.company_overview.split()) >= 5:
        score += 0.20
    # Is the overview substantive (not just "Company X is a company")?
    if intel.company_overview and len(intel.company_overview.split()) >= 20:
        score += 0.05

    # Target audience identified?
    if intel.target_audience and len(intel.target_audience.split()) >= 3:
        score += 0.15

    # Found at least one contact email?
    if intel.contact_emails:
        score += 0.15

    # Found at least one team member?
    if intel.key_team_members:
        score += 0.20
        # Found multiple? Even better.
        if len(intel.key_team_members) >= 2:
            score += 0.05

    # Any team members have LinkedIn URLs?
    has_linkedin = any(m.linkedin_url for m in intel.key_team_members)
    if has_linkedin:
        score += 0.10

    # Meta: if we have all the basics, it's a solid extraction
    has_basics = bool(intel.company_overview and intel.target_audience)
    if has_basics and intel.key_team_members:
        score += 0.10

    return min(1.0, score)
