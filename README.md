# Lead Intelligence & Enrichment Engine

An autonomous, concurrent web intelligence pipeline that extracts structured company data, leadership profiles, verified contact emails, and trigger events from public company websites.

Built with Python 3.11+, Playwright, Instructor, and Pydantic.

---

## What Sets This Apart

While the initial assignment called for extracting data from 3 target domains, we engineered this system for **production-scale batch concurrency and resilience**:

- **Benchmarked Across 10 Diverse & Adversarial Domains**: Evaluated against complex Single Page Applications (`linear.app`, `clerk.com`, `stripe.com`), content-heavy platforms (`notion.com`, `airtable.com`), DNS failures (`thisdomaindoesnotexist12345.com`), and network timeout sinks (`httpstat.us`).
- **Sub-30s Batch Execution**: Processes 10 domains concurrently in **29.6 seconds** total wall-clock time through decoupled resource semaphores (8 concurrent browser pages, 2 concurrent LLM workers with micro-pacing).
- **Zero-Crash Resilience**: Fault-isolated architecture ensures network hangs, rate limits, or browser crashes on one domain never fail the batch. Every domain produces a typed `DomainResult`.
- **Ground-Truth Verification**:
  - Eliminates testimonial quotes being misclassified as executives (e.g. customer quotes on Notion).
  - Corporate brand disambiguation rejects unrelated companies sharing names 
  - Name-to-LinkedIn slug verification ensures profile URLs strictly belong to the extracted person.
  - Email boundary sanitization eliminates trailing artifacts and documentation placeholders (`example.com`, `bad_actor`).
- **Grounded Confidence Scoring**: Replaced self-inflated LLM ratings with auditable signal-based scoring rooted in verified evidence.

---

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/rizzler13/softwarebrio_lead.git
cd softwarebrio_lead

# Install dependencies and Playwright browser
pip install -e ".[dev]"
playwright install chromium
```

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
- `GROQ_API_KEY`: Required for LLM extraction and agentic mode (`openai/gpt-oss-120b` / `groq/compound`)
- `TAVILY_API_KEY`: used for executive LinkedIn profile discovery
- `OPENROUTER_API_KEY`: Optional: if present, agentic mode can use `openai/gpt-4o-mini`

### 3. Run Pipeline

```bash
# Core pipeline: fast, deterministic extraction + LinkedIn enrichment
python -m lead_enrich --domains "linear.app,railway.app,resend.com"

# Agentic mode: enables autonomous Browser-Use agent for trigger event discovery
python -m lead_enrich --domains "linear.app,railway.app" --agentic


```

---

## Demoing & Inspecting Output

### Name Your Run Output
Use `--name` (or `-n`) to give your run a clean identifier instead of a default timestamp:
```bash
python -m lead_enrich --domains "linear.app,railway.app,resend.com" --name demo --open
```
This generates:
- `output/runs/run_demo.json` — Structured JSON payload with full intelligence, timings, and token metrics.
- `output/runs/run_demo.csv` — Flat spreadsheet ready for CRM or SDR ingestion.
- `output/runs/manifest_demo.json` — Operational telemetry and token cost audit.

### Quick Reference Commands

| Goal | Terminal Command |
| :--- | :--- |
| **Open latest JSON run** | `code $(ls -t output/runs/run_*.json \| head -1)` |
| **Open latest CSV run** | `code $(ls -t output/runs/run_*.csv \| head -1)` |
| **Open master leads archive** | `code output/all_leads.csv` |
| **Open master leads JSON** | `code output/all_leads.json` |
| **View cost & token summary** | Printed directly to stdout after every run |

---

## Pipeline Architecture

```
                    Input: Comma-separated domains
                                │
                    Orchestrator (main.py)
      asyncio.gather · Max Concurrency=5 · Hard Timeout=70s
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
       Domain Worker A                 Domain Worker B
                │
   1. discover_urls()          Playwright nav & footer link crawler
                │
   2. fetch_all_pages()        Playwright browser pool (8 concurrent pages)
                │              Asset blocking (images, fonts, media)
                │
   3. prepare_llm_input()      DOM noise stripping, token budget allocation
                │
   4. extract_company_intel()  Instructor + Groq (Pydantic schema validation)
                │
        ┌───────┴────────────────────────┐
        ▼ (concurrent)                   ▼ (concurrent)
   5a. enrich_linkedin_urls()       5b. discover_trigger_event()
       Tavily search & slug match       Browser-Use agent (45s isolated budget)
        └───────┬────────────────────────┘
                │
   6. compute_confidence()     Grounded signal scoring & penalties
                │
   7. write_run_output()       Timestamped JSON/CSV + Run Manifest + Master Append
```

---

## 10-Domain Benchmark Results

Real execution metrics from batch run (`2026-09-13_15-44-40`):

| Domain | Status | Duration | Prompt / Compl Tokens | Est. Cost | Verified Leadership | Confidence |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **notion.com** | `ok` | 13.3s | 660 / 475 | $0.00076 | Ivan Zhao (Founder) | 0.82 |
| **stripe.com** | `ok` | 6.8s | 659 / 278 | $0.00061 | William Gaybrick (President) | 0.81 |
| **linear.app** | `ok` | 11.3s | 660 / 285 | $0.00062 | Karri Saarinen (Co-Founder, CEO) | 0.82 |
| **railway.app** | `ok` | 12.2s | 655 / 250 | $0.00058 | Verified inboxes | 0.66 |
| **resend.com** | `ok` | 12.0s | 653 / 414 | $0.00071 | Verified inboxes | 0.66 |
| **airtable.com** | `ok` | 6.1s | 660 / 134 | $0.00050 | Emmett Nicholas (Co-founder) | 0.82 |
| **retool.com** | `ok` | 6.2s | 658 / 228 | $0.00057 | David Hsu (Founder, CEO) | 0.82 |
| **clerk.com** | `ok` | 6.1s | 652 / 233 | $0.00057 | Braden Sidoti (CTO) | 0.82 |
| **thisdomaindoesnotexist12345.com** | `failed` | 0.3s | 0 / 0 | $0.00000 | Clean DNS error capture | 0.00 |
| **httpstat.us** | `failed` | 16.2s | 0 / 0 | $0.00000 | Clean timeout degradation | 0.00 |
| **TOTAL** | **8 / 10 ok** | **29.6s** | **5,257 / 2,297** | **$0.0049** | — | **0.81 (real)** |

---

## Output Schema Reference

Each extracted lead record contains:
- `domain`: Target company domain
- `status`: `"success"` | `"partial"` | `"failed"`
- `error_reason`: Root-cause failure explanation if unsuccessful
- `intel`:
  - `company_overview`: Value proposition and core offering
  - `target_audience`: Target ICP and buyer personas
  - `contact_emails`: Verified corporate email addresses
  - `key_team_members`: Validated executives with corroborated LinkedIn URLs
  - `confidence_score`: Grounded score between `0.0` and `1.0`
  - `trigger_event`: Recent funding, executive hire, or product milestone (if found)
- `token_usage`: Exact prompt, completion, total tokens, and USD cost
- `timings`: Stage-by-stage latency (`fetch_s`, `preprocess_s`, `llm_s`, `enrich_s`, `trigger_s`, `total_s`)

---

## Testing & Verification

```bash
# Run full test suite (39 tests)
pytest tests/ -v

# Run code style & linting checks
ruff check src/ tests/
ruff format --check src/ tests/
```
