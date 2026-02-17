---
description: 'Use to validate a Python project by running all checks: ruff lint, format, mypy type checking, and pytest. Ensures project is CI-ready.'
---

# Python Project Validation

Full validation workflow for Python projects.

## Quick Validation

```bash
# Full validation (lint + format + typecheck + test)
ruff check src/ && ruff format --check src/ && mypy src/ && pytest

# With coverage
ruff check src/ && ruff format --check src/ && mypy src/ && pytest --cov=src
```

## Validation Steps

### 1. Lint Check (Ruff)

```bash
ruff check src/ tests/
```

**Fix issues:**
```bash
ruff check --fix src/ tests/
```

### 2. Format Check (Ruff)

```bash
ruff format --check src/ tests/
```

**Fix issues:**
```bash
ruff format src/ tests/
```

### 3. Type Check (mypy)

```bash
mypy src/

# Show error codes
mypy --show-error-codes src/
```

### 4. Run Tests

```bash
# Full test suite
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific file/directory
pytest tests/unit/
```

## Makefile

```makefile
.PHONY: lint format typecheck test validate fix

lint:
	ruff check src/ tests/

format:
	ruff format --check src/ tests/

typecheck:
	mypy src/

test:
	pytest

validate: lint format typecheck test

fix:
	ruff check --fix src/ tests/
	ruff format src/ tests/
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check src/

      - name: Format check
        run: ruff format --check src/

      - name: Type check
        run: mypy src/

      - name: Test
        run: pytest --cov=src --cov-report=xml

      - uses: codecov/codecov-action@v4
```

## Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Validation Checklist

| Check | Command | Fix |
|-------|---------|-----|
| Lint | `ruff check src/` | `ruff check --fix src/` |
| Format | `ruff format --check src/` | `ruff format src/` |
| Types | `mypy src/` | Add type annotations |
| Tests | `pytest` | Fix failing tests |
| Coverage | `pytest --cov=src` | Add tests |

## Common Issues

### Ruff violations
```bash
# See all issues with codes
ruff check src/

# Fix automatically
ruff check --fix src/

# Ignore specific rule
# noqa: E501
```

### Format issues
```bash
# Check what would change
ruff format --check --diff src/

# Fix all
ruff format src/
```

### mypy errors
```bash
# Show context
mypy --show-error-context src/

# Ignore specific error
x: int = value  # type: ignore[assignment]
```

### Test failures
```bash
# Run single test
pytest tests/test_foo.py::test_specific -v

# Show local variables
pytest --tb=long

# Stop on first failure
pytest -x
```

## uv Workflow

If using uv:

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Or with uv sync
uv sync --dev

# Run commands via uv
uv run ruff check src/
uv run pytest
```
