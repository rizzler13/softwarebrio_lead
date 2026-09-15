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


def _normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn post URLs or profile URLs to standard in/ URLs."""
    if not url:
        return ""
    clean = url.split("?")[0].rstrip("/")
    if "linkedin.com/in/" in clean:
        return clean
    m = re.search(r"linkedin\.com/posts/([a-zA-Z0-9_-]+?)_", clean)
    if m:
        return f"https://www.linkedin.com/in/{m.group(1)}"
    return clean


def _is_valid_person_name(name: str) -> bool:
    """Validate that a candidate string looks like a human person's name, not a sentence or post title."""
    name_tokens = name.strip().split()
    if not (2 <= len(name_tokens) <= 4):
        return False
    stop_words = {
        "how", "why", "what", "deciding", "accidentally", "chose", "my", "our",
        "the", "with", "from", "for", "and", "or", "in", "at", "to", "is", "we",
        "i", "did", "post", "activity", "comments", "read", "join", "see", "listen",
        "ep", "episode", "series", "thanks", "congrats", "welcoming", "introducing",
        "announcing", "excited", "happy", "proud", "reflection", "thoughts", "interview"
    }
    if any(tok.lower() in stop_words for tok in name_tokens):
        return False
    if any(not tok[0].isalpha() or (not tok[0].isupper() and tok.lower() not in ("de", "van", "von", "al")) for tok in name_tokens):
        return False
    if any(p in name for p in (".", "?", "!", '"', ";", ":", "/", "\\", "…", "...")):
        return False
    return True


def _parse_linkedin_title(
    title: str, url: str, domain: str, content: str = ""
) -> TeamMember | None:
    """
    Extract and validate name, role, and company alignment from LinkedIn search results.
    Checks title headline and snippet content, filtering out quotes and unrelated businesses.
    """
    url = _normalize_linkedin_url(url)
    if not title or not url or "linkedin.com/in/" not in url:
        return None

    brand = domain.split(".")[0].lower()
    title_lower = title.lower()
    content_lower = content.lower()

    # Target company brand must be mentioned in the title or snippet content
    if brand not in title_lower and brand not in content_lower:
        return None

    # Reject compound brands sharing the word (e.g. 'Hue & Stripe', 'Foggy Notion')
    if f"& {brand}" in title_lower or f"and {brand}" in title_lower:
        return None

    cleaned = title.replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
    parts = re.split(r"\s+[-–|]\s+", cleaned)
    if not parts or not parts[0].strip():
        return None

    name = parts[0].strip()
    if not _is_valid_person_name(name):
        return None

    if len(parts) >= 3 and EXEC_ROLE_PATTERN.search(parts[2]):
        candidate_comp = parts[1].strip()
        role = parts[2].strip()
        if not _is_matching_company(candidate_comp, brand):
            return None
    elif len(parts) > 1:
        role = parts[1].strip()
    else:
        role = ""

    # If role is missing from headline, infer from matching executive pattern in title or name-bound content
    if not role:
        match = EXEC_ROLE_PATTERN.search(title_lower)
        if match:
            role = f"{match.group(0).capitalize()} at {brand.capitalize()}"
        else:
            name_tokens = name.split()
            first_tok = name_tokens[0].lower()
            last_tok = name_tokens[-1].lower()
            c_match = re.search(
                rf"\b(?:{re.escape(first_tok)}|{re.escape(last_tok)})\b[^.\n]*?\b(co-?founder|ceo|cto|coo|founder|president)\b",
                content_lower,
            )
            if c_match:
                role = f"{c_match.group(1).capitalize()} at {brand.capitalize()}"
            else:
                return None

    # True executive/leadership keywords required in the role
    if not EXEC_ROLE_PATTERN.search(role):
        return None

    # Role or company affiliation must specifically tie to the target brand
    # (prevents matching someone whose surname happens to be the brand name, e.g. Diankha Linear)
    has_brand_affiliation = (
        brand in role.lower()
        or f"at {brand}" in content_lower
        or f"@{brand}" in content_lower
        or f"of {brand}" in content_lower
        or f"{brand} ceo" in content_lower
        or f"{brand} founder" in content_lower
        or f"{brand} president" in content_lower
    )
    if not has_brand_affiliation:
        return None

    # Role cannot simply be a corporate name (e.g. 'Retool Inc.')
    role_lower = role.lower()
    if role_lower.endswith(("inc.", "inc", "llc", "corp", "ltd", "gmbh")):
        return None

    # Verify company alignment: if the title explicitly mentions 'at ...', ensure it matches target domain
    comp_match = re.search(r"(?:at|@)\s+([A-Za-z0-9\s&,.'\"-]+)", role, re.IGNORECASE)
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
    clean_name = domain.split(".")[0].capitalize()
    brand = domain.split(".")[0].lower()

    try:
        # 1. Primary query targeting LinkedIn profile pages and executive roles
        results = await client.search(
            query=f"{clean_name} founders co-founders CEO CTO linkedin",
            include_domains=["linkedin.com"],
            max_results=8,
            search_depth="basic",
        )

        all_results = list(results.get("results", []))
        heuristic_leaders = []
        seen_names = set()

        for r in all_results:
            raw_url = r.get("url", "")
            url = _normalize_linkedin_url(raw_url)
            if "linkedin.com/in/" not in url:
                continue
            title = r.get("title", "")
            content = r.get("content", "")
            parsed = _parse_linkedin_title(title, url, domain, content=content)
            if parsed and _is_valid_person_name(parsed.name) and parsed.name.lower() not in seen_names:
                seen_names.add(parsed.name.lower())
                heuristic_leaders.append(parsed)
                if len(heuristic_leaders) >= 3:
                    return heuristic_leaders

        # 2. If heuristic parsing didn't find at least 2 leaders, use LLM extraction on search snippets
        if len(heuristic_leaders) < 2 and all_results and settings.groq_api_key:
            import instructor
            from groq import AsyncGroq

            snippets = []
            for r in all_results:
                u = _normalize_linkedin_url(r.get("url", ""))
                t = r.get("title", "")
                c = r.get("content", "")[:350]
                snippets.append(f"Title: {t}\nURL: {u}\nSnippet: {c}")

            try:
                groq_client = AsyncGroq(api_key=settings.groq_api_key)
                inst = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
                out = await inst.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"Extract the top 2-3 genuine founders / executive leaders (CEO, Co-founder, CTO) "
                                f"of {clean_name} ({domain}) and their LinkedIn profile URLs from these search results. "
                                "For URLs, ensure they are in https://www.linkedin.com/in/username format. "
                                "Do not extract customer quotes, investors, or lower-level employees. "
                                "Return valid JSON adhering to the schema."
                            ),
                        },
                        {"role": "user", "content": "\n\n".join(snippets)},
                    ],
                    response_model=_DiscoveredLeaders,
                    max_tokens=800,
                )
                for l in out.leaders:
                    if (
                        _is_valid_person_name(l.name)
                        and l.name.lower() not in seen_names
                        and (not l.linkedin_url or "linkedin.com/in/" in l.linkedin_url)
                    ):
                        seen_names.add(l.name.lower())
                        heuristic_leaders.append(l)
                        if len(heuristic_leaders) >= 3:
                            break
            except Exception as exc:
                log.debug("llm_founder_extraction_failed", domain=domain, error=str(exc))

        return heuristic_leaders

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
    - Preserves legitimate website-extracted team members without false drops.
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
        comp_match = re.search(r"(?:at|@)\s+([A-Za-z0-9\s&]+)", role_lower)
        if comp_match:
            comp = comp_match.group(1).strip()
            if not _is_matching_company(comp, brand):
                log.info("dropping_unrelated_site_extract", name=m.name, role=m.role, domain=domain)
                continue
        clean_members.append(m)
    intel.key_team_members = clean_members

    # 2. Enrich missing LinkedIn URLs for executive leaders extracted from site
    exec_roles = ["founder", "ceo", "cto", "cfo", "coo", "chief", "president", "vp", "head", "director", "lead"]
    members_needing_urls = [
        m
        for m in intel.key_team_members
        if not m.linkedin_url and m.name and any(kw in (m.role or "").lower() for kw in exec_roles)
    ]
    if members_needing_urls:
        target_members = members_needing_urls[:5]

        async def _search_member(member: TeamMember) -> None:
            query = f'"{member.name}" site:linkedin.com/in {brand}'
            try:
                results = await client.search(
                    query=query,
                    max_results=3,
                    search_depth="basic",
                )
                for result in results.get("results", []):
                    raw_url = result.get("url", "")
                    url = _normalize_linkedin_url(raw_url)
                    title = result.get("title", "")
                    content = result.get("content", "").lower()
                    title_lower = title.lower()
                    if "linkedin.com/in/" in url and _is_matching_linkedin_profile(
                        member.name, title, url
                    ):
                        if brand in title_lower or brand in content:
                            member.linkedin_url = url
                            log.info("linkedin_found", name=member.name, url=url)
                            break
            except Exception as exc:
                log.warning("tavily_search_error", name=member.name, error=str(exc))

        await asyncio.gather(*[_search_member(m) for m in target_members])

    # 3. External founder lookup if no executive leadership is present
    has_exec = any(
        EXEC_ROLE_PATTERN.search(m.role or "")
        for m in intel.key_team_members
    )
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
        if not _is_valid_person_name(m.name):
            continue
        role_lower = (m.role or "").lower()
        if not (m.role or "").strip() or role_lower.endswith(("inc.", "inc", "llc", "corp", "ltd")):
            continue
        comp_match = re.search(r"(?:at|@)\s+([A-Za-z0-9\s&]+)", role_lower)
        if comp_match:
            comp = comp_match.group(1).strip()
            if not _is_matching_company(comp, brand):
                continue
        verified_members.append(m)

    intel.key_team_members = verified_members
    return intel
