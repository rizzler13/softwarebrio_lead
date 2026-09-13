.PHONY: install install-dev test lint format run clean

install:
	pip install -e .
	playwright install chromium

install-dev:
	pip install -e ".[dev]"
	playwright install chromium

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

run:
	python3 -m lead_enrich --domains "postman.com,supabase.com,vapi.ai"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
