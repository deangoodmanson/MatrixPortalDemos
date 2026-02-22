# Contributing

Thanks for your interest in contributing to LED Matrix Portal Camera Feed!

## Branches

- `main` — stable, release-tagged
- Feature branches — create from `main`, open a PR when ready

## Pull Requests

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Ensure all CI checks pass (see below)
4. Open a PR with a clear description and test plan

## Running Checks Locally

### Pro version

```bash
cd pro
uv sync --all-groups

uv run pytest tests/ -v      # 159 unit tests
uv run ruff check src/        # lint
uv run ruff format src/       # format
uv run ty check               # type check
# or all at once:
make check
```

### HS version

```bash
cd hs
uv sync --all-groups

uv run ruff check src/
uv run ty check src/
```

### Utils

```bash
cd utils
uv sync --all-groups

uv run pytest tests/ -v
uv run ruff check src/
uv run ty check
```

## Code Style

- **Pro**: strict typing, Google-style docstrings, `ruff` formatting (100-char lines, double quotes)
- **HS**: extensive inline comments for students, simple type hints (`Optional`, `Tuple`), 120-char lines
- No `TODO`, `FIXME`, or `HACK` comments — open an issue instead

## Hardware Modules

`capture/` and `transport/` in `pro/` are not unit tested — they require real hardware. Don't add unit tests that mock these; instead document integration test steps in your PR.

## Firmware (`matrix-portal/`)

CircuitPython code is not CI-tested. Test manually on a physical Matrix Portal M4 and describe your test steps in the PR.

## Versioning

This project uses [Semantic Versioning](https://semver.org/). Version numbers are in `pyproject.toml` for each component. Update the version and add an entry to `CHANGELOG.md` for any release PR.
