# Lead Intelligence & Enrichment Engine

An autonomous, concurrent web intelligence, and optionally deploy an autonomous browser agent to discover timely trigger events.

Built with Python 3.11+, Playwright, Instructor, Pydantic, and Browser-Use.

---

## Why This Exists (And How I Built It)

Most lead scraping tools fall into one of two extremes:
1. **Dumb regex/HTML scrapers** that break the moment a company changes their CSS or uses a Single Page Application (SPA).
2. **Brittle "pure agent" setups** that spend 2 minutes and 50,000 tokens clicking around randomly just to find an "About" page.

I built this pipeline around a **hybrid, two-tier architecture**:
- **The Fast Path (Deterministic & Fast)**: Uses headless Playwright with aggressive asset blocking (dropping images, fonts, and stylesheets) to crawl core navigation and footer links. It strips DOM noise, budgets tokens tightly, and uses Instructor with Groq (`openai/gpt-oss-120b`) for validated, typed Pydantic extraction. Then, it uses Tavily to cross-reference and verify executive LinkedIn profiles.
- **The Deep Path (Agentic & Autonomous)**: When run with `--agentic`, it hands off to a bounded `browser-use` sub-agent. The agent specifically hunts for genuine trigger events—like recent Series A/B funding rounds, leadership changes, or major product launches from the last 12 months—without wasting steps or hallucinating events.

---

## Key Engineering Decisions

### 1. Decoupled Concurrency & Strict Resource Semaphores
Running multiple browser instances while simultaneously hitting LLM inference endpoints easily leads to resource contention and 429 rate limits.
- The pipeline isolates domain workers with `asyncio.gather`, but caps concurrent browser pages and LLM calls via dedicated internal semaphores.
- If a target domain has a dead DNS record, times out, or triggers bot mitigation, the failure is trapped in that domain's isolated error boundary. It records a structured `DomainResult` with the failure reason and execution timings, and the rest of the batch completes uninterrupted.

### 2. Ground-Truth Verification Over Hallucinated Data
LLMs have a bad habit of hallucinating plausible-looking data when given messy HTML. To keep data high quality:
- **Testimonial Rejection**: Filters out customer quotes masquerading as company executives (e.g. customer testimonials on landing pages).
- **Brand & Company Disambiguation**: Cross-checks executive LinkedIn search results against the target company's actual brand and domain, discarding people with matching names who work at completely different firms.
- **Strict Name-to-Slug Matching**: Ensures returned LinkedIn URLs actually match the person's name rather than returning a generic directory or unrelated profile.
- **Clean Inboxes**: Validates email format and strips trailing punctuation, junk characters, and documentation placeholders (`example.com`, `domain.com`).

### 3. Grounded Confidence Scoring
Instead of asking an LLM "how confident are you?" (which almost always answers 0.95+), the confidence score is calculated deterministically from verified signals:
- Base score is awarded for presence and quality of core fields (overview, target audience, verified emails, executive team).
- For agentic trigger events, confidence requires strict corroboration:
  - **No Bare Homepage Citations**: The agent cannot cite `https://company.com/` for a funding round; it must point to the specific blog post, press release, or changelog URL.
  - **Substantive Text Overlap**: Summary keywords must genuinely appear in the visited page text (using word-boundary matching so words like `fundamental` don't trigger a false positive for `fund`).
  - Unsubstantiated or ungrounded claims are strictly hard-capped at $\le 0.30$.

### 4. Token & Cost Efficiency
- Preprocessing token budgeting keeps prompt payloads compact (~1,000 tokens per domain).
- Average cost runs at less than **$0.001 per domain** on the core extraction path, with execution times hovering around 6–12 seconds per domain.

---

## Quick Start

### 1. Prerequisites & Installation

```bash
# Clone the repository
git clone https://github.com/rizzler13/softwarebrio_lead.git
cd softwarebrio_lead

# Install dependencies (requires Python 3.11+)
pip install -e ".[dev]"

# Install Playwright Chromium binaries
playwright install chromium
```

### 2. Environment Configuration

Copy the sample environment file:
```bash
cp .env.example .env
```

Add your API keys to `.env`:
```env
# Required: Fast LLM extraction via Groq (e.g. openai/gpt-oss-120b)
GROQ_API_KEY=gsk_your_groq_key_here

# Optional: Executive LinkedIn discovery & verification
TAVILY_API_KEY=tvly-your_tavily_key_here

# Optional: For agentic mode using OpenAI/OpenRouter models
OPENROUTER_API_KEY=sk-or-your_openrouter_key_here
```

---

## Running the Pipeline

### Core Mode (Fast & Deterministic)
Extracts structured company overview, target audience, verified inboxes, and executive leadership profiles:
```bash
python -m lead_enrich --domains "vapi.ai, supabase.com, postman.com"
```

### Agentic Mode (Autonomous Trigger Discovery)
Spawns the `browser-use` agent to actively navigate the company's site, hunt down blog/press pages, and extract verified trigger events from the last 12 months:
```bash
python -m lead_enrich --domains "vapi.ai, supabase.com" --agentic
```

### Choosing an LLM Provider for the Trigger Agent
You can specify the LLM backend for the agentic stage via `--provider`:
```bash
# Auto mode: prompts interactively or picks based on available keys
python -m lead_enrich --domains "vapi.ai --agentic --provider auto

# Use OpenRouter (gpt-4o-mini) with Groq fallback
python -m lead_enrich --domains "vapi.ai" --agentic --provider both

# Force Groq only (groq/compound) or OpenRouter only
python -m lead_enrich --domains "vapi.ai" --agentic --provider groq
```

### Naming Runs & Inspecting Results
Give your run a clean identifier and open the resulting files automatically:
```bash
# Runs the batch, saves outputs as run_demo.*, and opens in VS Code
python -m lead_enrich --domains "vapi.ai, supabase.com" --name demo --open
```

### CLI Options

| Flag | Shorthand | Description |
| :--- | :---: | :--- |
| `--domains` | | Comma-separated domains to process (e.g. `"linear.app,stripe.com"`). |
| `--agentic` | | Enables the autonomous browser agent for trigger event discovery. |
| `--provider` | | Trigger agent LLM: `auto`, `both`, `openrouter`, or `groq`. |
| `--name` | `-n` | Custom run name identifier (e.g. `--name batch1` $\rightarrow$ `run_batch1.json`). |
| `--open` | | Automatically opens the generated JSON and CSV in your editor. |
| `--verbose` | `-v` | Enables detailed, step-by-step logs of browser and agent actions. |

---

## Output Structure

Every run creates isolated artifacts in `output/runs/` and appends to a cumulative master archive:

```
output/
├── all_leads.csv              # Cumulative master CSV of all runs
├── all_leads.json             # Cumulative master JSON of all runs
└── runs/
    ├── run_<id>.json          # Full structured JSON for this run
    ├── run_<id>.csv           # Flat CSV export formatted for CRM / SDR ingestion
    └── manifest_<id>.json     # Run metadata, timings, model name, and token cost breakdown
```

### Sample Lead Record Schema

```json
{
  "domain": "linear.app",
  "status": "success",
  "error_reason": null,
  "intel": {
    "company_overview": "Purpose-built tool for modern software development teams...",
    "target_audience": "Software engineering, product management, and design teams.",
    "contact_emails": ["support@linear.app", "sales@linear.app"],
    "key_team_members": [
      {
        "name": "Karri Saarinen",
        "role": "Co-Founder & CEO",
        "linkedin_url": "https://www.linkedin.com/in/karrisaarinen"
      }
    ],
    "confidence_score": 0.82,
    "trigger_event": {
      "found": true,
      "event_type": "product_news",
      "summary": "Announced Linear Asks and new customer support integrations.",
      "source_url": "https://linear.app/blog/linear-asks",
      "estimated_date": "2026-04",
      "confidence": 0.80
    }
  },
  "token_usage": {
    "prompt_tokens": 660,
    "completion_tokens": 285,
    "total_tokens": 945,
    "cost_usd": 0.00062
  },
  "timings": {
    "fetch_s": 2.4,
    "preprocess_s": 0.1,
    "llm_s": 1.2,
    "enrich_s": 2.1,
    "trigger_s": 5.5,
    "total_s": 11.3
  }
}
```

---

## Testing & Quality

The project includes a comprehensive test suite (46 automated tests) covering Pydantic models, DOM preprocessing, LinkedIn title parsing, trigger agent degradation, and confidence scoring:

```bash
# Run tests
pytest

# Run linter and formatting checks
ruff check src/ tests/
ruff format --check src/ tests/
```

---

## Architecture Flow

```
                 Input: Comma-separated domains
                               │
               Orchestrator (asyncio.gather)
             Bounded Concurrency & Error Bounds
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
         Domain Worker A               Domain Worker B
                │
   1. discover_urls()       Playwright link discovery & footer crawl
                │
   2. fetch_all_pages()     Parallel page fetch with asset blocking
                │
   3. prepare_llm_input()   Noise stripping & 1000-token budget packing
                │
   4. extract_company()     Instructor + Groq structured extraction
                │
        ┌───────┴────────────────────────┐
        ▼ (concurrent)                   ▼ (concurrent, optional)
   5a. enrich_linkedin()            5b. discover_trigger_event()
       Tavily search & slug match       Browser-Use agent (bounded budget)
        └───────┬────────────────────────┘
                │
   6. compute_confidence()  Grounded multi-signal confidence scoring
                │
   7. write_run_output()    run_<id>.json, run_<id>.csv, manifest_<id>.json
```
