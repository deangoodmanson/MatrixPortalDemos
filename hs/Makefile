.PHONY: help install lint format typecheck ci clean

# Default target
help:
	@echo "LED Portal HS - Development Commands"
	@echo ""
	@echo "  make install    Install all dependencies with uv"
	@echo "  make lint       Run ruff linter"
	@echo "  make format     Format code with ruff"
	@echo "  make typecheck  Run ty type checker"
	@echo "  make ci         Run the exact CI gate (lint, typecheck)"
	@echo "  make clean      Remove caches and build artifacts"

install:
	uv sync --all-groups

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

typecheck:
	uv run ty check src/

# Exact CI gate — mirrors .github/workflows/ci.yml (hs job).
# Note: the HS CI job runs no tests and no format check; it scopes to src/.
ci: lint typecheck
	@echo "CI checks passed!"

clean:
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
