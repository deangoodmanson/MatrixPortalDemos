.PHONY: help install lint format typecheck test ci clean

# Default target
help:
	@echo "LED Portal Utils - Development Commands"
	@echo ""
	@echo "  make install    Install all dependencies with uv"
	@echo "  make lint       Run ruff linter"
	@echo "  make format     Format code with ruff"
	@echo "  make typecheck  Run ty type checker"
	@echo "  make test       Run unit tests"
	@echo "  make ci         Run the exact CI gate (test, lint, typecheck)"
	@echo "  make clean      Remove caches and build artifacts"

install:
	uv sync --all-groups

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run ty check

test:
	uv run pytest tests/ -v

# Exact CI gate — mirrors .github/workflows/ci.yml (utils job).
# Note: the utils CI job does NOT run `ruff format --check`.
ci: test lint typecheck
	@echo "CI checks passed!"

clean:
	rm -rf .ruff_cache .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
