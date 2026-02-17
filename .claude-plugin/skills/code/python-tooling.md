---
description: 'Use for Python linting, formatting, type checking, test coverage, and project validation. Covers ruff, mypy, pytest-cov.'
---

# Python Tooling

Comprehensive guide to Python linting, formatting, type checking, and coverage.

## Linting & Formatting: Ruff (Recommended)

Modern all-in-one tool (replaces Black, isort, Flake8):

### Installation

```bash
pip install ruff
```

### Configuration

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "RUF",    # Ruff-specific
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ARG"]

[tool.ruff.lint.isort]
known-first-party = ["myapp"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

### Commands

```bash
# Lint check
ruff check src/

# Lint with autofix
ruff check --fix src/

# Format check
ruff format --check src/

# Format with autofix
ruff format src/

# Both lint and format
ruff check --fix src/ && ruff format src/
```

## Type Checking: mypy

### Installation

```bash
pip install mypy
```

### Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = ["pandas.*", "numpy.*"]
ignore_missing_imports = true
```

### Commands

```bash
# Check all
mypy src/

# Check specific file
mypy src/order.py

# Show error codes
mypy --show-error-codes src/
```

## Type Checking: pyright (Faster)

```bash
pip install pyright
pyright
```

## Test Coverage: pytest-cov

### Installation

```bash
pip install pytest pytest-cov
```

### Commands

```bash
# Run with coverage
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html

# With minimum threshold
pytest --cov=src --cov-fail-under=80
```

## Project Validation

Run all checks:

```bash
# Check everything
ruff check src/ && ruff format --check src/ && mypy src/ && pytest

# Fix everything
ruff check --fix src/ && ruff format src/
```

## Makefile

```makefile
.PHONY: install lint format typecheck test check fix

install:
	pip install -e ".[dev]"

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

test:
	pytest

check: lint typecheck test

fix:
	ruff check --fix src/ tests/
	ruff format src/ tests/
```

## Pre-commit Hooks

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

      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

## Quick Reference

| Operation | Command |
|-----------|---------|
| Lint check | `ruff check src/` |
| Lint fix | `ruff check --fix src/` |
| Format check | `ruff format --check src/` |
| Format fix | `ruff format src/` |
| Type check | `mypy src/` |
| Test | `pytest` |
| Coverage | `pytest --cov=src` |
| All checks | `ruff check && ruff format --check && mypy src/ && pytest` |
| All fixes | `ruff check --fix && ruff format` |

## Recommended Stack

- **Lint/Format**: Ruff (fast, replaces multiple tools)
- **Types**: mypy with strict mode
- **Testing**: pytest with pytest-cov
