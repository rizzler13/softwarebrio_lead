"""Tests for text preprocessing — the stuff between raw page content and LLM input."""

from lead_enrich.models import PageContent
from lead_enrich.preprocessor import clean_text, count_tokens, prepare_llm_input


class TestCleanText:
    def test_collapses_whitespace(self):
        raw = "Hello\n\n\n\n\nWorld\n\n\n\nFoo"
        cleaned = clean_text(raw)
        # Should have at most 2 consecutive newlines
        assert "\n\n\n" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned

    def test_removes_cookie_banners(self):
        raw = "Welcome to our site\nAccept all cookies\nWe use cookies to improve your experience"
        cleaned = clean_text(raw)
        assert "cookie" not in cleaned.lower()
        assert "Welcome" in cleaned

    def test_deduplicates_repeated_lines(self):
        raw = "Home\nAbout\nContact\nHome\nAbout\nContact\nHome\nAbout\nContact"
        cleaned = clean_text(raw)
        # Each line should appear at most twice
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
        for unique_line in set(lines):
            assert lines.count(unique_line) <= 2

    def test_preserves_real_content(self):
        raw = "Our company builds developer tools that help teams ship faster."
        cleaned = clean_text(raw)
        assert cleaned == raw


class TestCountTokens:
    def test_basic_count(self):
        tokens = count_tokens("Hello world")
        assert tokens > 0
        assert tokens < 10  # "Hello world" is ~2-3 tokens

    def test_longer_text(self):
        text = "word " * 100
        tokens = count_tokens(text)
        assert tokens > 50  # should be roughly 100 tokens


class TestPrepareLlmInput:
    def test_respects_token_budget(self):
        # Create a page with a lot of text
        long_text = "This is a test sentence. " * 500
        pages = [PageContent(url="https://example.com/about", text=long_text)]
        result = prepare_llm_input(pages, token_budget=200)
        tokens = count_tokens(result)
        # Should be under budget (with some margin for headers)
        assert tokens <= 250  # small margin for the page header

    def test_prioritizes_about_pages(self):
        pages = [
            PageContent(url="https://example.com/pricing", text="Pricing info here"),
            PageContent(url="https://example.com/about", text="About us content here"),
        ]
        result = prepare_llm_input(pages, token_budget=5000)
        # About page should appear before pricing
        about_pos = result.find("about")
        pricing_pos = result.find("pricing")
        assert about_pos < pricing_pos

    def test_skips_error_pages(self):
        pages = [
            PageContent(url="https://example.com/good", text="Good content"),
            PageContent(url="https://example.com/bad", text="", error="timeout"),
        ]
        result = prepare_llm_input(pages, token_budget=5000)
        assert "good" in result.lower()
        assert "bad" not in result.lower()

    def test_includes_emails_in_header(self):
        pages = [
            PageContent(
                url="https://example.com",
                text="Contact us",
                emails=["hello@example.com"],
            ),
        ]
        result = prepare_llm_input(pages, token_budget=5000)
        assert "hello@example.com" in result
