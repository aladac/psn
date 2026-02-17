---
description: 'Use to validate a Rust project by running all checks: clippy, format, type checking, and tests. Ensures project is CI-ready.'
---

# Rust Project Validation

Full validation workflow for Rust projects.

## Quick Validation

```bash
# Full validation (format + lint + test)
cargo fmt -- --check && cargo clippy -- -D warnings && cargo test

# With all features
cargo fmt -- --check && \
cargo clippy --all-targets --all-features -- -D warnings && \
cargo test --all-features
```

## Validation Steps

### 1. Format Check

```bash
cargo fmt -- --check
```

**Fix issues:**
```bash
cargo fmt
```

### 2. Type Check

```bash
# Fast check without building
cargo check

# All targets (tests, examples, benches)
cargo check --all-targets --all-features
```

### 3. Lint (Clippy)

```bash
# Standard check
cargo clippy

# CI mode (warnings = errors)
cargo clippy -- -D warnings

# All targets and features
cargo clippy --all-targets --all-features -- -D warnings
```

**Fix issues:**
```bash
cargo clippy --fix --allow-dirty
```

### 4. Run Tests

```bash
# All tests
cargo test

# With all features
cargo test --all-features

# Specific test
cargo test test_name
```

## Makefile

```makefile
.PHONY: check lint test validate fix

check:
	cargo check --all-targets --all-features

lint:
	cargo clippy --all-targets --all-features -- -D warnings

test:
	cargo test --all-features

validate:
	cargo fmt -- --check
	cargo clippy --all-targets --all-features -- -D warnings
	cargo test --all-features

fix:
	cargo fmt
	cargo clippy --fix --allow-dirty
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

env:
  CARGO_TERM_COLOR: always

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy

      - uses: Swatinem/rust-cache@v2

      - name: Format check
        run: cargo fmt -- --check

      - name: Clippy
        run: cargo clippy --all-targets --all-features -- -D warnings

      - name: Test
        run: cargo test --all-features

      - name: Doc
        run: cargo doc --no-deps
```

## Pre-commit Hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
cargo fmt -- --check || exit 1
cargo clippy -- -D warnings || exit 1
cargo test --quiet || exit 1
```

## Validation Checklist

| Check | Command | Fix |
|-------|---------|-----|
| Format | `cargo fmt -- --check` | `cargo fmt` |
| Types | `cargo check` | Fix compiler errors |
| Lint | `cargo clippy -- -D warnings` | `cargo clippy --fix` |
| Tests | `cargo test` | Fix failing tests |
| Docs | `cargo doc --no-deps` | Fix doc comments |

## Common Issues

### Format violations
```bash
# Check what would change
cargo fmt -- --check

# Fix all
cargo fmt
```

### Clippy warnings
```bash
# See all warnings
cargo clippy

# Fix automatically where possible
cargo clippy --fix --allow-dirty

# Allow specific lint in code
#[allow(clippy::lint_name)]
```

### Test failures
```bash
# Run specific test with output
cargo test test_name -- --nocapture

# Run tests in single thread
cargo test -- --test-threads=1
```

### Build errors
```bash
# Clean and rebuild
cargo clean && cargo build

# Check specific target
cargo check --lib
cargo check --bin mybin
```
