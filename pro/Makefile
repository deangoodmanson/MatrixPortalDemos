.PHONY: help install install-dev lint format typecheck check run run-mac run-pi test clean

# Default target
help:
	@echo "LED Portal Pro - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install production dependencies with uv"
	@echo "  make install-dev  Install all dependencies including dev tools"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Format code with ruff"
	@echo "  make typecheck    Run ty type checker"
	@echo "  make check        Run all checks (lint, format check, typecheck)"
	@echo ""
	@echo "Running:"
	@echo "  make run          Run with default config"
	@echo "  make run-mac      Run with macOS config"
	@echo "  make run-pi       Run with Raspberry Pi config"
	@echo "  make run-test     Run in test mode (no display)"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run unit tests"
	@echo ""
	@echo "Other:"
	@echo "  make clean        Remove generated files"

# Installation
install:
	uv sync

install-dev:
	uv sync --all-extras

# Code quality
lint:
	uv run ruff check src/

format:
	uv run ruff format src/

format-check:
	uv run ruff format --check src/

typecheck:
	uv run ty check src/

check: lint format-check typecheck
	@echo "All checks passed!"

# Running
run:
	uv run ledportal

run-mac:
	uv run ledportal --config config/mac.yaml

run-pi:
	uv run ledportal --config config/pi.yaml

run-test:
	uv run ledportal --no-display

run-bw:
	uv run ledportal --bw

# Testing
test:
	uv run pytest tests/ -v

# Cleanup
clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf src/**/__pycache__
	rm -rf .ruff_cache
	rm -f *.bmp
	rm -f *.bin
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
