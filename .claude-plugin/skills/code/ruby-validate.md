---
description: 'Use to validate a Ruby project by running all checks: lint, format, type checking, and tests. Ensures project is CI-ready.'
---

# Ruby Project Validation

Full validation workflow for Ruby projects.

## Quick Validation

```bash
# Full validation (lint + typecheck + test)
bundle exec standardrb && bundle exec srb tc && bundle exec rspec

# With coverage
bundle exec standardrb && bundle exec srb tc && bundle exec rspec --format documentation
```

## Validation Steps

### 1. Lint Check (StandardRuby)

```bash
bundle exec standardrb
```

**Fix issues:**
```bash
bundle exec standardrb --fix
```

### 2. Type Check (Sorbet)

```bash
# If using Sorbet
bundle exec srb tc

# Specific strictness
bundle exec srb tc --typed=strict
```

### 3. Run Tests

```bash
# Full test suite
bundle exec rspec

# With coverage report
COVERAGE=true bundle exec rspec

# Specific file/directory
bundle exec rspec spec/services/
```

## Makefile

```makefile
.PHONY: lint typecheck test validate fix

lint:
	bundle exec standardrb

typecheck:
	bundle exec srb tc

test:
	bundle exec rspec

validate: lint typecheck test

fix:
	bundle exec standardrb --fix
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

      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3'
          bundler-cache: true

      - name: Lint
        run: bundle exec standardrb

      - name: Type check
        run: bundle exec srb tc

      - name: Test
        run: bundle exec rspec
```

## Pre-commit Hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
bundle exec standardrb --fix
bundle exec srb tc
bundle exec rspec --fail-fast
```

## Validation Checklist

| Check | Command | Fix |
|-------|---------|-----|
| Lint | `standardrb` | `standardrb --fix` |
| Types | `srb tc` | Add signatures |
| Tests | `rspec` | Fix failing tests |
| Coverage | `COVERAGE=true rspec` | Add tests |

## Common Issues

### StandardRuby violations
```bash
# See all issues
bundle exec standardrb --format progress

# Fix automatically
bundle exec standardrb --fix
```

### Sorbet errors
```bash
# Generate RBI files for gems
bundle exec srb rbi gems

# Update Sorbet files
bundle exec srb rbi update
```

### Test failures
```bash
# Run single failing test
bundle exec rspec spec/path/to_spec.rb:42

# Run with verbose output
bundle exec rspec --format documentation
```
