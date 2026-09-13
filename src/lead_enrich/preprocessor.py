"""
Text preprocessing — turns raw page text into something the LLM can work with
without burning through the token budget.

this module does the heavy lifting of cleaning, deduplication, and budget enforcement.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import tiktoken

from lead_enrich.models import PageContent

# cl100k_base is GPT-4's encoding — close enough to Llama's tokenizer
# for budget estimation. The exact count doesn't matter, we just need
# a reasonable proxy to stay under limits.
_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Approximate token count using cl100k_base encoding."""
    return len(_encoder.encode(text, disallowed_special=()))


def clean_text(raw: str) -> str:
    """
    Strip the noise from extracted page text.

    Playwright's inner_text() already removes HTML tags, but we still get
    cookie banners, repeated nav items, and walls of whitespace.
    """
    # Collapse runs of whitespace and blank lines
    text = re.sub(r"\n{3,}", "\n\n", raw)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Remove common boilerplate phrases that add nothing
    noise_patterns = [
        r"(?i)accept\s*(all\s*)?cookies?",
        r"(?i)we\s+use\s+cookies",
        r"(?i)cookie\s+policy",
        r"(?i)privacy\s+policy\s+terms",
        r"(?i)©\s*\d{4}.*?(?:all\s+rights\s+reserved|inc\.|ltd\.)",
        r"(?i)subscribe\s+to\s+(our\s+)?newsletter",
        r"(?i)follow\s+us\s+on",
        r"(?i)skip\s+to\s+(main\s+)?content",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text)

    # Deduplicate lines and drop isolated button/menu labels
    lines = text.split("\n")
    seen_count: dict[str, int] = {}
    deduped = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Drop standalone button labels / very short nav words that add no value
        if len(stripped.split()) <= 2 and stripped.lower() in {
            "sign in",
            "sign up",
            "log in",
            "get started",
            "learn more",
            "contact sales",
            "read more",
            "see all",
            "view all",
            "try free",
            "start free",
            "book a demo",
            "talk to sales",
        }:
            continue
        seen_count[stripped] = seen_count.get(stripped, 0) + 1
        if seen_count[stripped] <= 2:
            deduped.append(stripped)

    return "\n".join(deduped).strip()


def _page_priority(page: PageContent) -> int:
    """Higher priority pages get more of the token budget."""
    parsed = urlparse(page.url)
    path = parsed.path.rstrip("/")
    if not path or path == "":
        return 4  # Homepage is primary source for overview and target audience
    url_lower = page.url.lower()
    if any(kw in url_lower for kw in ["about", "team", "company", "leadership"]):
        return 3  # Company & leadership details
    if any(kw in url_lower for kw in ["contact", "people"]):
        return 2
    if any(kw in url_lower for kw in ["pricing", "careers"]):
        return 1
    return 2


def prepare_llm_input(pages: list[PageContent], token_budget: int) -> str:
    """
    Merge and trim page content to fit strictly within the token budget.

    Strategy: prioritize about/team pages, truncate lower-value pages first.
    Uses exact token truncation to guarantee the LLM input never exceeds the budget.
    """
    sorted_pages = sorted(pages, key=_page_priority, reverse=True)

    sections: list[str] = []
    tokens_used = 0

    for page in sorted_pages:
        if not page.text or page.error:
            continue

        cleaned = clean_text(page.text)
        if not cleaned:
            continue

        # Concise header with URL, meta description, and emails
        header = f"[{page.url}]"
        if page.meta_description:
            header += f"\nMeta: {page.meta_description.strip()}"
        if page.emails:
            header += f"\nEmails found: {', '.join(page.emails[:3])}"

        section = f"{header}\n{cleaned}"
        encoded_section = _encoder.encode(section)
        section_tokens = len(encoded_section)

        remaining = token_budget - tokens_used
        if remaining <= 0:
            break

        if section_tokens <= remaining:
            sections.append(section)
            tokens_used += section_tokens
        else:
            # Token-exact truncation: decode only what fits in the remaining budget
            truncated = _encoder.decode(encoded_section[:remaining]) + "\n[...]"
            sections.append(truncated)
            tokens_used += remaining
            break

    return "\n\n".join(sections)
