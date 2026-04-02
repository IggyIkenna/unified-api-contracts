.PHONY: help setup quality-gates test lint format typecheck coverage install clean

help:
	@echo "Available targets:"
	@echo "  setup         - Full dev environment setup (Python 3.13 + uv + venv + deps)"
	@echo "  quality-gates  - Run all quality gates (lint, format, typecheck, test with coverage)"
	@echo "  test          - Run tests"
	@echo "  lint          - Run ruff linter"
	@echo "  format        - Run ruff formatter"
	@echo "  typecheck     - Run basedpyright type checker"
	@echo "  coverage      - Run tests with coverage reporting"
	@echo "  install       - Install development dependencies (assumes venv active)"
	@echo "  clean         - Clean build artifacts"

setup:
	@bash scripts/setup.sh

quality-gates:
	@echo "Running quality gates..."
	ruff check . --fix
	ruff format .
	basedpyright unified_api_contracts/
	pytest --cov=unified_api_contracts --cov-report=term-missing

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	basedpyright unified_api_contracts/

coverage:
	pytest --cov=unified_api_contracts --cov-report=term-missing --cov-report=html

install:
	uv pip install -e "."

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
# Fix import patterns
.PHONY: fix-imports
fix-imports:
	@echo "🔧 Fixing import patterns..."
	@python3 .cursor/scripts/check-import-patterns.py --fix

# Check import patterns
.PHONY: check-imports
check-imports:
	@echo "🔍 Checking import patterns..."
	@python3 .cursor/scripts/check-import-patterns.py --verbose
