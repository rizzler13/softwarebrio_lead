# Lead Enrichment Agent

An autonomous pipeline that takes company domains, crawls their public web presence, and extracts structured intelligence using an LLM. Built for the SoftwareBrio technical assignment.

## What it does

Give it a list of domains. It visits each one, figures out which pages matter (about, team, contact — discovered dynamically, not hardcoded), reads them with a headless browser, cleans the text down to what's actually useful, sends it to an LLM for structured extraction, and enriches missing LinkedIn URLs via search. Every domain produces a result, even if it fails.

## Quick start

```bash
# Clone and install
git clone https://github.com/rizzler13/softwarebrio_lead.git
cd softwarebrio_lead
pip install -e ".[dev]"
playwright install chromium

# Set up your API keys
cp .env.example .env
# Edit .env with your GROQ_API_KEY (required) and TAVILY_API_KEY (optional)

# Run it
python -m lead_enrich --domains "postman.com,supabase.com,vapi.ai"
```

Or use the Makefile:

```bash
make install-dev  # installs everything including dev tools
make run          # runs against the 3 test domains
make test         # runs the test suite
make lint         # checks code style
```

## Architecture

```
Input: ["postman.com", "supabase.com", "vapi.ai"]
         │
    Orchestrator (main.py)
    asyncio.gather + semaphore (max 3 concurrent)
    per-domain timeout ceiling (30s)
         │
         ▼  for each domain:
    ┌────────────────────────────┐
    │ 1. discover_urls()         │  Parse nav/footer links, rank by keyword relevance
    │ 2. fetch_pages()           │  Playwright async, render JS, extract visible text
    │ 3. preprocess()            │  Strip boilerplate, enforce token budget
    │ 4. extract()               │  Instructor + Groq → validated Pydantic model
    │ 5. enrich()                │  Tavily search for missing LinkedIn URLs
    │ 6. score_confidence()      │  70% signal-based + 30% LLM self-assessment
    │ 7. write_output()          │  JSON + CSV
    └────────────────────────────┘
```

Every stage is a separate module you could test or replace independently.

## Design decisions

**Why Playwright over Selenium?** Native async support, faster page loads, better JS rendering for modern SPAs. Selenium requires thread pool hacks for concurrency and its API shows its age.

**Why Instructor over raw JSON parsing?** Instructor maps LLM output directly onto Pydantic models via tool calling. No regex on completions, no `json.loads` on raw text, no schema drift. If the LLM returns bad data, Instructor retries with the validation error — the extraction either succeeds or fails cleanly.

**Why dynamic URL discovery instead of hardcoding `/about`, `/team`?** Hardcoding paths is the naive version. Real company sites use all kinds of URL structures (`/company/about-us`, `/our-team`, `/who-we-are`). We parse the actual navigation and rank by keyword relevance. Falls back to well-known paths only if discovery finds nothing.

**Why blended confidence scoring?** Pure LLM self-assessment overestimates (LLMs are bad at knowing what they don't know). Pure signal-based scoring misses nuance. We use 70% deterministic signals (did we find an email? team members? substantive overview?) + 30% LLM self-assessment. The formula is in `scorer.py` — transparent and auditable.

## Confidence score — worked example

Here's how the score breaks down for a real extraction (Postman):

```
Signal checks:                               Weight
✅ Has company overview (≥5 words)            +0.20
✅ Overview is substantive (≥20 words)        +0.05
✅ Has target audience (≥3 words)             +0.15
✅ Has ≥1 contact email                       +0.15
✅ Has ≥1 team member                         +0.20
✅ Has ≥2 team members                        +0.05
❌ Has team member with LinkedIn URL          +0.00
✅ Has overview + audience + team (basics)    +0.10
                                              ─────
Signal score:                                  0.90
LLM self-assessment:                           0.80

Blended: 0.7 × 0.90 + 0.3 × 0.80 = 0.87
```

The LinkedIn URL gap drops the signal from 1.0 to 0.90 — which is correct, because missing LinkedIn data genuinely limits the lead's usefulness for outreach.

## Error handling

Every domain produces a `DomainResult` with `status: "success" | "partial" | "failed"`. Failed domains include an `error_reason` explaining what went wrong. The pipeline uses:

- **Per-domain try/except** — one crash never kills the batch
- **asyncio.wait_for timeout** — 30s ceiling per domain
- **tenacity retries** — exponential backoff on LLM rate limits
- **Graceful degradation** — missing Tavily key? LinkedIn enrichment skips silently

## Performance & per-stage latency breakdown

The pipeline instruments granular timers across every phase of execution:
- **Fetch**: Headless browser URL discovery and parallel page fetching (shared Playwright browser, asset blocking for images/media/fonts)
- **Preproc**: Text extraction, boiler-plate stripping, and token budgeting
- **LLM**: Schema-constrained entity extraction via Instructor + Groq
- **Search**: Tavily LinkedIn enrichment and external founder discovery

A detailed breakdown prints at the conclusion of every run:

```
                   Pipeline Performance & Token Usage Report                    
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Domain                     ┃ Status  ┃  Fetch ┃ Prepr… ┃    LLM ┃ Search ┃ Total Time ┃ Tokens (P / C / Tot) ┃ Est. Cost ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ postman.com                │ success │  7.68s │ 0.009s │  1.45s │  5.69s │     14.83s │    3465 / 237 / 3702 │   $0.0022 │
├────────────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────────┼──────────────────────┼───────────┤
│ supabase.com               │ success │  4.65s │ 0.028s │  4.54s │  6.37s │     15.59s │    3471 / 270 / 3741 │   $0.0023 │
├────────────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────────┼──────────────────────┼───────────┤
│ vapi.ai                    │ success │  2.96s │ 0.006s │  2.81s │ 20.33s │     26.11s │    3193 / 256 / 3449 │   $0.0021 │
├────────────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────────┼──────────────────────┼───────────┤
│ diffusiononmlx.netlify.app │ success │  5.11s │ 0.004s │  1.51s │  6.37s │     13.00s │    3791 / 202 / 3993 │   $0.0024 │
├────────────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────────┼──────────────────────┼───────────┤
│ arize.com                  │ success │  7.22s │ 0.004s │ 45.36s │  2.50s │     55.09s │    3461 / 265 / 3726 │   $0.0023 │
└────────────────────────────┴─────────┴────────┴────────┴────────┴────────┴────────────┴──────────────────────┴───────────┘
```

## Project structure

```
├── src/lead_enrich/
│   ├── main.py           # CLI + orchestrator
│   ├── models.py          # Pydantic schemas
│   ├── browser.py         # Playwright URL discovery + page fetching
│   ├── preprocessor.py    # Text cleaning + token budget
│   ├── extractor.py       # Instructor + Groq LLM extraction
│   ├── enricher.py        # Tavily LinkedIn search fallback
│   ├── scorer.py          # Confidence score computation
│   ├── cost_tracker.py    # Token usage reporting
│   ├── writer.py          # JSON/CSV output
│   └── config.py          # Settings from .env
├── tests/
│   ├── test_models.py     # Schema validation
│   ├── test_preprocessor.py
│   ├── test_scorer.py
│   └── test_pipeline.py   # E2E with mocked failures
├── output/                # Generated output files
├── pyproject.toml
├── Makefile
├── guide.md               # Engineering decisions log
└── .github/workflows/ci.yml
```

## Running tests

```bash
pytest tests/ -v
```

The test suite includes unit tests for models, preprocessing, and scoring, plus end-to-end tests that mock failure scenarios (timeout, browser crash, empty pages) and verify the pipeline produces proper error records instead of crashing.

## Requirements

- Python 3.11+
- A Groq API key (free at https://console.groq.com)
- Optionally, a Tavily API key for LinkedIn enrichment (free tier at https://app.tavily.com)
