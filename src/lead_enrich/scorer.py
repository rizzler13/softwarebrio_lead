"""
Confidence scoring — assesses extraction completeness, data quality, and
verifies that leadership and email signals are legitimate.

Prevents false confidence: if leadership is unverified or missing, confidence
is honestly capped rather than masked with an inflated score.
"""

from __future__ import annotations

from lead_enrich.models import CompanyIntel


def compute_confidence(intel: CompanyIntel) -> float:
    """
    Compute a verified confidence score from 0.0 to 1.0.

    Weights: 70% signal-based verification, 30% LLM self-assessment.
    """
    signal_score = _check_signals(intel)
    llm_score = intel.confidence_score

    # Signal-based verification takes priority over self-assessment
    blended = 0.70 * signal_score + 0.30 * llm_score
    return round(max(0.0, min(1.0, blended)), 2)


def _check_signals(intel: CompanyIntel) -> float:
    """
    Rigorously score lead quality based on verified signals and penalty deductions.
    """
    score = 0.0

    # 1. Company Overview (max 0.25)
    words_overview = len(intel.company_overview.split())
    if words_overview >= 8:
        score += 0.25
    elif words_overview >= 4:
        score += 0.15

    # 2. Target Audience (max 0.20)
    words_aud = len(intel.target_audience.split())
    if words_aud >= 4:
        score += 0.20
    elif words_aud >= 2:
        score += 0.10

    # 3. Valid Contact Emails (max 0.15)
    if intel.contact_emails:
        dummy_markers = ["example.com", "bad_actor"]
        has_dummy = any(
            any(m in email for m in dummy_markers) for email in intel.contact_emails
        )
        if not has_dummy:
            score += 0.15
        else:
            score -= 0.10  # penalty for placeholder emails

    # 4. Key Leadership Verification (max 0.35)
    exec_keywords = [
        "founder",
        "co-founder",
        "ceo",
        "cto",
        "coo",
        "president",
        "chief",
        "vp",
        "head",
    ]
    verified_execs = 0
    penalty = 0.0

    for m in intel.key_team_members:
        role_lower = (m.role or "").lower()
        has_exec_title = any(k in role_lower for k in exec_keywords)

        # Suspicious roles without title or ending with corporate suffix
        if (
            not has_exec_title
            or role_lower.endswith(("inc.", "inc", "llc", "corp", "ltd"))
            or not m.name.strip()
        ):
            penalty += 0.10
            continue

        verified_execs += 1
        # Bonus for verified LinkedIn profile URL
        if m.linkedin_url and "linkedin.com/in/" in m.linkedin_url:
            score += 0.08

    if verified_execs >= 1:
        score += 0.15
    if verified_execs >= 2:
        score += 0.05

    score = max(0.0, score - penalty)

    # Honesty cap: if leadership is unverified or empty, confidence cannot exceed 0.70
    if verified_execs == 0:
        return round(min(0.70, score), 2)

    return round(min(1.0, score), 2)
