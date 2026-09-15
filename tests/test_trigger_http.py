"""
Tests for Phase 1: HTTP-based trigger event discovery.

Verifies:
1. Funding keyword regex patterns (dollar amounts, round names, verbs)
2. Article link extraction from mock HTML
3. Date extraction and recency scoring
4. Confidence thresholds and event type classification
5. Summary extraction from article text
"""

from __future__ import annotations

from lead_enrich.trigger_http import (
    _DOLLAR_PATTERN,
    _FUNDRAISE_VERB_PATTERN,
    _ROUND_PATTERN,
    _extract_article_links,
    _extract_summary,
    _score_trigger_text,
    _strip_html,
)


class TestFundingRegex:
    """Test regex patterns for funding signal detection."""

    def test_dollar_amounts(self):
        assert _DOLLAR_PATTERN.search("raised $50M in Series B")
        assert _DOLLAR_PATTERN.search("secures $120 million")
        assert _DOLLAR_PATTERN.search("$1.2B valuation")
        assert _DOLLAR_PATTERN.search("raised $500K seed round")
        assert not _DOLLAR_PATTERN.search("costs $5 per month")

    def test_round_names(self):
        assert _ROUND_PATTERN.search("announces Series A")
        assert _ROUND_PATTERN.search("closes seed round")
        assert _ROUND_PATTERN.search("pre-seed funding")
        assert _ROUND_PATTERN.search("Series C extension")
        assert not _ROUND_PATTERN.search("a series of events")

    def test_fundraise_verbs(self):
        assert _FUNDRAISE_VERB_PATTERN.search("company raised $50M")
        assert _FUNDRAISE_VERB_PATTERN.search("secures funding")
        assert _FUNDRAISE_VERB_PATTERN.search("round led by Sequoia")
        assert _FUNDRAISE_VERB_PATTERN.search("announces $30M funding")
        assert _FUNDRAISE_VERB_PATTERN.search("backed by a16z")


class TestStripHtml:
    """Test HTML to text conversion."""

    def test_removes_script_tags(self):
        html = '<div>Hello</div><script>alert("x")</script><div>World</div>'
        text = _strip_html(html)
        assert "Hello" in text
        assert "World" in text
        assert "alert" not in text

    def test_removes_style_tags(self):
        html = "<style>.x { color: red; }</style><p>Content</p>"
        text = _strip_html(html)
        assert "Content" in text
        assert "color" not in text

    def test_converts_block_elements_to_newlines(self):
        html = "<h1>Title</h1><p>Paragraph</p>"
        text = _strip_html(html)
        assert "Title" in text
        assert "Paragraph" in text

    def test_decodes_html_entities(self):
        html = "<p>AT&amp;T raised $50M</p>"
        text = _strip_html(html)
        assert "AT&T" in text


class TestScoreTriggerText:
    """Test confidence scoring for trigger event signals."""

    def test_strong_funding_signal(self):
        text = "Company X raised $50M in Series B funding led by Sequoia Capital."
        conf, etype, date = _score_trigger_text(text)
        assert conf >= 0.70
        assert etype == "funding"

    def test_dollar_plus_round(self):
        text = "Announces $120M Series C round."
        conf, etype, _ = _score_trigger_text(text)
        assert conf >= 0.65
        assert etype == "funding"

    def test_dollar_plus_verb(self):
        text = "The startup raised $20 million from investors."
        conf, etype, _ = _score_trigger_text(text)
        assert conf >= 0.65
        assert etype == "funding"

    def test_leadership_change(self):
        text = "Acme Corp appoints Jane Doe as new CEO."
        conf, etype, _ = _score_trigger_text(text)
        assert conf >= 0.50
        assert etype == "leadership_change"

    def test_product_news(self):
        text = "Company launches general availability of their new platform."
        conf, etype, _ = _score_trigger_text(text)
        assert conf >= 0.40
        assert etype == "product_news"

    def test_no_signals(self):
        text = "Welcome to our website. We build great software for teams."
        conf, etype, _ = _score_trigger_text(text)
        assert conf < 0.30

    def test_date_extraction(self):
        text = "Raised $50M Series B in September 2026."
        _, _, date = _score_trigger_text(text)
        assert date is not None
        assert "2026" in date

    def test_iso_date_extraction(self):
        text = "Funding announced on 2026-09-15."
        conf, _, date = _score_trigger_text(text)
        assert date == "2026-09-15"


class TestExtractArticleLinks:
    """Test article link extraction from HTML."""

    def test_extracts_blog_links(self):
        html = '''
        <div>
            <a href="/blog/series-b-announcement">We Raised $50M in Series B</a>
            <a href="/blog/product-update">New Feature Release</a>
            <a href="/about">About Us</a>
        </div>
        '''
        links = _extract_article_links(html, "https://example.com")
        assert len(links) >= 1
        # Funding link should be prioritized
        assert any("series-b" in link["url"] for link in links)

    def test_funding_links_sorted_first(self):
        html = '''
        <div>
            <a href="/blog/product-update">New dark mode is here</a>
            <a href="/blog/series-b">We raised $50M in Series B from Sequoia</a>
            <a href="/blog/team-retreat">Team offsite recap</a>
        </div>
        '''
        links = _extract_article_links(html, "https://example.com")
        assert links[0]["url"].endswith("series-b")

    def test_skips_short_text_links(self):
        html = (
            '<a href="/blog/post">OK</a>'
            '<a href="/blog/article">This is a proper article title</a>'
        )
        links = _extract_article_links(html, "https://example.com")
        assert all(len(link["text"]) >= 10 for link in links)


class TestExtractSummary:
    """Test summary extraction from article text."""

    def test_extracts_first_sentences(self):
        text = (
            "We are thrilled to announce our Series B funding round. "
            "Led by Sequoia Capital, this $50M investment will fuel our growth. "
            "The team is excited about the road ahead."
        )
        summary = _extract_summary(text)
        assert "Series B" in summary
        assert len(summary) <= 300

    def test_skips_nav_sentences(self):
        text = "Skip to main content. Cookie policy. We raised $50M today."
        summary = _extract_summary(text)
        assert "raised" in summary
        assert "Skip to" not in summary

    def test_handles_empty_text(self):
        assert _extract_summary("") == ""
        assert _extract_summary("   ") == ""
