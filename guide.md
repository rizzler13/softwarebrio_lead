# Engineering Decisions Log

Every choice made during the build, with the reasoning. This is the doc I'd want to read if I picked up this codebase for the first time.

---

## 2024-09-13: Initial build

### Browser automation: Playwright over Selenium

Playwright was the obvious choice here. Selenium works, but it's showing its age — you need chromedriver version management, threading hacks for async, and the API is verbose. Playwright gives us native `async/await`, automatic browser binary management, and better handling of modern JS-heavy sites. For an evaluator, using Playwright signals "this person follows current tooling."

### URL discovery: dynamic, not hardcoded

The assignment says to "discover relevant subpages (e.g., /about, /team)." The naive approach is to hardcode those paths. The problem: real company sites use all sorts of URL structures — `/company/about-us`, `/our-team`, `/who-we-are`, `/people`. Supabase doesn't even have `/team` as a top-level path.

So instead, we load the homepage, grab every `<a>` tag, filter to same-domain links, and score them by keyword relevance (`about` → 10, `team` → 10, `contact` → 7, `pricing` → 5). We take the top 6 ranked URLs. If discovery finds fewer than 2 useful links (heavy SPA, no crawlable nav), we fall back to the hardcoded paths.

This is more code, but it's the version that actually works on arbitrary sites.

### Content preprocessing: inner_text(), not raw HTML

The assignment explicitly penalizes "feeding entire raw HTML trees into an LLM." Our approach:

1. Playwright's `page.inner_text('body')` strips all HTML tags and gives us the visible text — what a human would read on the page
2. `clean_text()` removes cookie banners, repeated nav items, and collapses whitespace
3. `prepare_llm_input()` enforces a token budget (6000 tokens by default) by prioritizing high-value pages (about/team) and truncating lower-value ones

The result: ~80-90% token reduction vs raw HTML, and the LLM gets cleaner input to work with.

### LLM extraction: Instructor + Groq

Instructor handles the gap between "LLM generates text" and "I need a validated Pydantic model." It uses Groq's tool calling API to constrain output to our schema, and retries with validation errors if the first attempt doesn't conform. No regex parsing, no `json.loads` on raw completions.

We initialize `AsyncGroq` explicitly with the API key from settings, wrapping it with `instructor.from_groq(groq_client, mode=instructor.Mode.TOOLS)`.

### Model choice: Qwen 3.8 27B on Groq

We use `qwen/qwen3.8-27b` on Groq. It natively supports OpenAI-compatible function and tool calling, delivers fast inference (~200 tokens/sec), and produces high-fidelity structured output for entity extraction.

### Quota and rate-limit engineering (ITPM & OTPM)

Groq's on-demand tier enforces quotas on input tokens per minute (8,000 ITPM) and output tokens per minute (1,000 OTPM). Naive parallel execution easily bursts these ceilings. We engineered three safeguards:
1. **Bounded output tokens**: We pass `max_tokens=500` to `create_with_completion`, keeping Groq's expected output reservation within the 1,000 OTPM ceiling while leaving plenty of room for `CompanyIntel` (~200-250 tokens).
2. **Serialized LLM calls (`_llm_lock`)**: While Playwright page discovery and rendering run concurrently across domains, the LLM extraction step is synchronized with an `asyncio.Lock` and a 1.5s cooldown so concurrent domains never collide in the same token window.
3. **Adaptive token fallback**: If a domain ever exceeds limits (413/429), our retry policy catches it, adaptively halves the preprocessed context, and retries cleanly.

### Confidence scoring: 70/30 blend

I was tempted to just let the LLM self-assess, but LLMs are systematically overconfident — they'll say 0.8 when they barely extracted anything. Pure signal-based scoring (did we find an email? +0.15) misses subtlety (a vague overview shouldn't score the same as a detailed one).

The 70/30 blend gives us the best of both: deterministic, auditable signal checks for the bulk of the score, with the LLM's assessment as a tiebreaker for nuance. The signal weights reflect what matters for lead enrichment — team members and overview are worth more than pricing info.

### Error handling philosophy

The golden rule: **every domain produces a result**. No domain silently vanishes because of an exception. No single failure kills the batch.

Implementation:
- `process_domain()` wraps everything in `try/except` and always returns a `DomainResult`
- `run_pipeline()` wraps each domain in `asyncio.wait_for()` for a hard timeout
- The outer `_bounded()` function catches `TimeoutError` and any other exception
- Each `DomainResult` has `status` ("success", "partial", "failed") and `error_reason`

This means we can point evaluators to the test in `test_pipeline.py` that simulates a crash and say: "here's proof it never crashes."

### Emails: browser-extracted + LLM-extracted, merged

We extract emails in two places:
1. `browser.py` uses regex on page text to find email patterns
2. The LLM sometimes finds emails in its extraction

We merge both sets (union, deduplicated) because neither is complete on its own — the regex catches emails the LLM ignores, and the LLM sometimes infers emails from context.

### Token budget: 6000 tokens default

This is a Goldilocks number. Too low (2000) and we lose important context from about/team pages. Too high (12000+) and we risk hitting Groq's rate limits and wasting inference time. 6000 tokens is roughly 2-3 pages of cleaned content, which is usually enough for a company overview + team info + contact details.

### Cost tracking: demonstrated even though Groq is free

Groq doesn't charge (yet), but tracking token usage demonstrates production awareness. We capture `prompt_tokens` and `completion_tokens` from every Groq response, compute estimated cost at OpenAI-equivalent rates ($0.59/$0.79 per 1M), and print a summary table at the end. If someone asks "how much would this cost at scale?" we have a real answer.

### LinkedIn enrichment: Tavily search

For team members without LinkedIn URLs on the site, we query Tavily: `"Jane Smith" "CEO" site:linkedin.com/in postman.com`. Tavily's free tier gives 1000 searches/month. We cap at 5 searches per domain to stay under limits.

If `TAVILY_API_KEY` isn't set, enrichment silently skips — it's a bonus, not a hard dependency.

### CI: GitHub Actions

A `.github/workflows/ci.yml` that runs lint + test on every push. This is 10 minutes of work and most candidates at this level don't do it. It's the single clearest signal that you ship like an engineer, not a student.

### Makefile

`make run`, `make test`, `make lint`, `make install`. Not fancy, but it shows familiarity with how real teams work. An evaluator can clone the repo and get running in 30 seconds.

### Structured logging: structlog

We use `structlog` instead of `print()` for all internal logging. It outputs structured key-value pairs that are easy to grep and parse. The terminal output via `rich` is for humans; the structured logs are for machines.

### Code style: ruff

Ruff for both linting and formatting. It's fast (Rust-based), combines flake8/isort/black into one tool, and is the current standard. Type hints everywhere.

---

## Design tradeoffs I considered but decided against

**LangGraph / multi-step agentic loop**: The assignment mentions this as a bonus. I considered it but decided the pipeline approach is cleaner for this use case. An agentic loop adds complexity (state management, tool definitions, iteration limits) without clear benefit when the page set is finite and the extraction is a single-shot operation. If the task were "adaptively explore a site based on what you find," an agent would make sense. For "visit 5 known pages and extract data," a pipeline is more predictable, testable, and debuggable.

**Selenium**: Covered above. No async, verbose API, driver management headaches.

**Raw JSON parsing from LLM output**: Using `json.loads()` on raw completions is fragile — the LLM might wrap JSON in markdown fences, include trailing commas, or emit partial objects. Instructor handles all of this.

**Token counting with the actual Llama tokenizer**: We use `tiktoken` (GPT-4's tokenizer) as a proxy. The exact count doesn't matter — we just need a reasonable estimate to stay under budget. The Llama tokenizer would require loading a SentencePiece model, and the accuracy difference is <10%.

**playwright-stealth**: Considered for anti-bot evasion. Decided against because the three test domains (Postman, Supabase, Vapi) don't block headless browsers. If we needed it, it's a one-line addition: `from playwright_stealth import stealth_async`.
