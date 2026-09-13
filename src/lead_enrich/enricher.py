"""
LinkedIn and leadership enrichment — uses search (Tavily) to:
1. Discover founders/executives and LinkedIn profiles when not found on the website.
2. Find LinkedIn profile URLs for team members extracted from the site missing links.

Degrades gracefully: if TAVILY_API_KEY isn't configured, returns data unchanged.
"""

from __future__ import annotations

import asyncio
import re

import structlog
from pydantic import BaseModel

from lead_enrich.config import Settings
from lead_enrich.models import CompanyIntel, TeamMember

log = structlog.get_logger()


class _DiscoveredLeaders(BaseModel):
    leaders: list[TeamMember]


VALID_CORP_SUFFIXES = {
    "inc",
    "inc.",
    "llc",
    "corp",
    "corporation",
    "ltd",
    "app",
    "hq",
    "technologies",
    "software",
    "ai",
    "co",
    "labs",
}

EXEC_ROLE_PATTERN = re.compile(
    r"\b(founder|co-founder|ceo|cto|coo|cpo|cro|cmo|president|chief executive|co-ceo)\b",
    re.IGNORECASE,
)


def _is_matching_company(comp: str, brand: str) -> bool:
    """Validate that a company name matches the brand, allowing only standard corporate suffixes."""
    comp_clean = comp.lower().strip().strip(".,")
    brand_clean = brand.lower().strip()
    if comp_clean == brand_clean:
        return True
    words = comp_clean.split()
    if not words:
        return False
    if words[0] == brand_clean and len(words) > 1:
        extra = " ".join(words[1:]).strip(".,")
        return extra in VALID_CORP_SUFFIXES
    return False


def _is_matching_linkedin_profile(name: str, title: str, url: str) -> bool:
    """
    Validate that a LinkedIn search hit actually belongs to the person requested.
    Checks if at least one meaningful name segment appears in the profile slug or title.
    """
    if not url or "linkedin.com/in/" not in url:
        return False
    name_parts = [p.lower() for p in re.findall(r"[a-zA-Z]{3,}", name)]
    if not name_parts:
        return True

    slug = url.rstrip("/").split("/")[-1].lower()
    title_lower = title.lower()

    # Reject common non-person slugs
    if slug in ("in", "jobs", "company", "pub"):
        return False

    return any(p in slug for p in name_parts) or any(p in title_lower for p in name_parts)


def _parse_linkedin_title(title: str, url: str, domain: str) -> TeamMember | None:
    """
    Extract and validate name, role, and company alignment from LinkedIn search result titles.
    Filters out customer quotes, unrelated businesses, and non-executive roles.
    """
    if not title or not url or "linkedin.com/in/" not in url:
        return None

    brand = domain.split(".")[0].lower()
    title_lower = title.lower()

    # Target company brand must be mentioned in the title
    if brand not in title_lower:
        return None

    # Reject compound brands sharing the word (e.g. 'Hue & Stripe', 'Foggy Notion')
    if f"& {brand}" in title_lower or f"and {brand}" in title_lower:
        return None

    cleaned = title.replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
    parts = re.split(r"\s+[-–|]\s+", cleaned)
    if len(parts) < 2:
        return None

    name = parts[0].strip()
    role = parts[1].strip()

    # Must look like a real name (at least 2 words, no generic words)
    name_tokens = name.split()
    if len(name_tokens) < 2 or any(
        tok.lower() in ("profile", "jobs", "overview", "experience", "inc", "ltd", "consultants")
        for tok in name_tokens
    ):
        return None

    # True executive/leadership keywords (word boundary prevents matching 'director' as 'cto')
    if not EXEC_ROLE_PATTERN.search(role):
        return None

    # Role cannot simply be a corporate name (e.g. 'Retool Inc.')
    role_lower = role.lower()
    if role_lower.endswith(("inc.", "inc", "llc", "corp", "ltd", "gmbh")):
        return None

    # Verify company alignment: if the title mentions 'at ...', ensure it matches target domain
    comp_match = re.search(r"(?:at|@|of)\s+([A-Za-z0-9\s&,.'\"-]+)", role, re.IGNORECASE)
    if comp_match:
        comp = comp_match.group(1).strip()
        if not _is_matching_company(comp, brand):
            return None
    else:
        # Check comma-separated company (e.g. "CEO, Linear Capital")
        comma_parts = role.split(",")
        if len(comma_parts) > 1:
            candidate_comp = comma_parts[-1].strip()
            if brand in candidate_comp.lower() and not _is_matching_company(candidate_comp, brand):
                return None

    # Validate that the LinkedIn URL slug corresponds to this person
    if not _is_matching_linkedin_profile(name, title, url):
        return None

    return TeamMember(name=name, role=role, linkedin_url=url)


async def _lookup_founders_external(domain: str, settings: Settings, client) -> list[TeamMember]:
    """Search for company founders / executives on LinkedIn if absent from the website."""
    # Search with the exact domain to ensure results belong strictly to this company
    query = f'"{domain}" (founder OR CEO OR "co-founder") site:linkedin.com/in'

    try:
        results = await client.search(query=query, max_results=5, search_depth="basic")

        # 1. Try zero-latency title parsing first with strict company validation
        heuristic_leaders = []
        for r in results.get("results", []):
            url = r.get("url", "")
            title = r.get("title", "")
            parsed = _parse_linkedin_title(title, url, domain)
            if parsed:
                heuristic_leaders.append(parsed)
                if len(heuristic_leaders) >= 3:
                    break

        if heuristic_leaders:
            return heuristic_leaders

        # 2. Adaptive fallback to LLM only if heuristic found nothing
        snippets = []
        for r in results.get("results", []):
            url = r.get("url", "")
            if "linkedin.com/in/" in url:
                title = r.get("title", "")
                content = r.get("content", "")[:250]
                snippets.append(f"Title: {title}\nURL: {url}\nSnippet: {content}")

        if not snippets:
            return []

        import instructor
        from groq import AsyncGroq

        groq_client = AsyncGroq(api_key=settings.groq_api_key)
        inst_client = instructor.from_groq(groq_client, mode=instructor.Mode.TOOLS)

        system_msg = (
            f"Extract the real founders or top C-level executives of the company at {domain} "
            "from these search results. Only include legitimate leaders of this exact company. "
            "Reject unrelated companies, customers, or consultants. Max 2 people."
        )

        response = await inst_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": f"Company: {domain}\n\nSearch results:\n" + "\n\n".join(snippets),
                },
            ],
            response_model=_DiscoveredLeaders,
            max_tokens=450,
        )

        valid_leaders = []
        for m in response.leaders:
            if m.linkedin_url and _is_matching_linkedin_profile(m.name, m.role, m.linkedin_url):
                valid_leaders.append(m)
        return valid_leaders[:2]

    except Exception as exc:
        log.warning("external_founder_lookup_failed", domain=domain, error=str(exc))
        return []


async def enrich_linkedin_urls(
    intel: CompanyIntel, domain: str, settings: Settings
) -> CompanyIntel:
    """
    Enrich company intelligence with LinkedIn profiles via search:
    - If no founders or leaders were found on the site, searches externally for them.
    - For team members extracted from the site missing URLs, looks up their profile URLs.
    - Sanitizes and purges customer quotes, unrelated company hits, and mismatched URLs.
    """
    if not settings.tavily_api_key:
        log.info("tavily_skipped", reason="no API key configured")
        return intel

    try:
        from tavily import AsyncTavilyClient
    except ImportError:
        log.warning("tavily_not_installed", hint="pip install tavily-python")
        return intel

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)

    brand = domain.split(".")[0].lower()

    # 1. Early filtering: drop members whose explicit company doesn't match target domain
    clean_members: list[TeamMember] = []
    for m in intel.key_team_members:
        role_lower = (m.role or "").lower().strip()
        if not role_lower or role_lower.endswith(("inc.", "inc", "llc", "corp", "ltd")):
            continue
        comp_match = re.search(r"(?:at|@|of)\s+([A-Za-z0-9\s&]+)", role_lower)
        if comp_match:
            comp = comp_match.group(1).strip()
            if not _is_matching_company(comp, brand):
                log.info("dropping_unrelated_site_extract", name=m.name, role=m.role, domain=domain)
                continue
        clean_members.append(m)
    intel.key_team_members = clean_members

    # 2. Enrich missing LinkedIn URLs for extracted leaders & detect customer quotes
    exec_roles = ["founder", "ceo", "cto", "cfo", "coo", "chief", "president", "vp", "head"]
    members_needing_urls = [
        m
        for m in intel.key_team_members
        if not m.linkedin_url and m.name and any(kw in (m.role or "").lower() for kw in exec_roles)
    ]
    if members_needing_urls:
        target_members = members_needing_urls[:2]

        async def _search_member(member: TeamMember) -> None:
            query = f'"{member.name}" site:linkedin.com/in {brand}'
            try:
                results = await client.search(
                    query=query,
                    max_results=3,
                    search_depth="basic",
                )
                for result in results.get("results", []):
                    url = result.get("url", "")
                    title = result.get("title", "")
                    content = result.get("content", "").lower()
                    title_lower = title.lower()
                    if "linkedin.com/in/" in url and _is_matching_linkedin_profile(
                        member.name, title, url
                    ):
                        # Verify that the LinkedIn hit belongs to target brand (guards
                        # against customer quotes like 'Michael Truell' from Cursor on Notion)
                        if brand in title_lower or brand in content:
                            member.linkedin_url = url
                            log.info("linkedin_found", name=member.name, url=url)
                            break
                        else:
                            log.info(
                                "customer_quote_detected",
                                name=member.name,
                                title=title,
                                domain=domain,
                            )
                            member.role = "__DROP__"
                            break
            except Exception as exc:
                log.warning("tavily_search_error", name=member.name, error=str(exc))

        await asyncio.gather(*[_search_member(m) for m in target_members])

    # Purge detected customer quotes
    intel.key_team_members = [m for m in intel.key_team_members if m.role != "__DROP__"]

    # 3. External founder lookup if no executive leadership is present
    has_exec = any(EXEC_ROLE_PATTERN.search(m.role or "") for m in intel.key_team_members)
    if not intel.key_team_members or not has_exec:
        external_leaders = await _lookup_founders_external(domain, settings, client)
        if external_leaders:
            existing_names = {m.name.lower() for m in intel.key_team_members}
            for leader in external_leaders:
                if leader.name.lower() not in existing_names:
                    intel.key_team_members.append(leader)
                    log.info(
                        "external_founder_found",
                        name=leader.name,
                        role=leader.role,
                        url=leader.linkedin_url,
                    )

    # 4. Final sanitization pass
    verified_members: list[TeamMember] = []
    for m in intel.key_team_members:
        role_lower = (m.role or "").lower()
        if not (m.role or "").strip() or role_lower.endswith(("inc.", "inc", "llc", "corp", "ltd")):
            continue
        comp_match = re.search(r"(?:at|@|of)\s+([A-Za-z0-9\s&]+)", role_lower)
        if comp_match:
            comp = comp_match.group(1).strip()
            if not _is_matching_company(comp, brand):
                continue
        verified_members.append(m)

    intel.key_team_members = verified_members
    return intel
