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


def _parse_linkedin_title(title: str, url: str) -> TeamMember | None:
    """
    Fast, zero-latency extraction of name and role from LinkedIn search result titles.
    Avoids expensive LLM round-trips for standard LinkedIn result patterns.
    """
    if not title or not url or "linkedin.com/in/" not in url:
        return None
    cleaned = title.replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
    parts = re.split(r"\s+[-–|]\s+", cleaned)
    if len(parts) >= 2:
        name = parts[0].strip()
        role = parts[1].strip()
        skip_words = ["profile", "linkedin", "jobs", "overview", "experience"]
        if any(skip in name.lower() for skip in skip_words):
            return None
        if len(name) >= 3:
            return TeamMember(name=name, role=role, linkedin_url=url)
    elif len(parts) == 1 and parts[0]:
        name = parts[0].strip()
        if len(name) >= 3 and not any(skip in name.lower() for skip in ["profile", "linkedin"]):
            return TeamMember(name=name, role="Executive / Founder", linkedin_url=url)
    return None


async def _lookup_founders_external(domain: str, settings: Settings, client) -> list[TeamMember]:
    """Search for company founders / executives on LinkedIn if absent from the website."""
    clean_name = domain.split(".")[0].capitalize()
    query = f'site:linkedin.com/in "{clean_name}" (founder OR CEO OR "co-founder")'

    try:
        results = await client.search(query=query, max_results=5, search_depth="basic")

        # 1. Try zero-latency title parsing first
        heuristic_leaders = []
        for r in results.get("results", []):
            url = r.get("url", "")
            title = r.get("title", "")
            parsed = _parse_linkedin_title(title, url)
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
            f"Extract the real founders or top C-level executives of {clean_name} ({domain}) "
            "and their exact LinkedIn URLs from search results. Only include legitimate leaders "
            "with their real linkedin.com/in/ URL. Max 3 people."
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
            max_tokens=300,
        )
        return response.leaders[:3]
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

    # 1. External founder lookup if no team members or founders were identified on-site
    has_exec = any(
        kw in (m.role or "").lower()
        for m in intel.key_team_members
        for kw in ["founder", "ceo", "chief executive", "president", "co-founder"]
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

    # 2. Enrich missing LinkedIn URLs for executive leaders extracted from site
    exec_roles = ["founder", "ceo", "cto", "cfo", "coo", "chief", "president", "vp", "head"]
    members_needing_urls = [
        m
        for m in intel.key_team_members
        if not m.linkedin_url
        and m.name
        and any(kw in (m.role or "").lower() for kw in exec_roles)
    ]
    if members_needing_urls:
        target_members = members_needing_urls[:2]

        async def _search_member(member: TeamMember) -> None:
            query = f'"{member.name}" "{member.role}" site:linkedin.com/in {domain}'
            try:
                results = await client.search(
                    query=query,
                    max_results=3,
                    search_depth="basic",
                )
                for result in results.get("results", []):
                    url = result.get("url", "")
                    if "linkedin.com/in/" in url:
                        member.linkedin_url = url
                        log.info(
                            "linkedin_found",
                            name=member.name,
                            url=url,
                        )
                        break
            except Exception as exc:
                log.warning("tavily_search_error", name=member.name, error=str(exc))

        await asyncio.gather(*[_search_member(m) for m in target_members])

    return intel
