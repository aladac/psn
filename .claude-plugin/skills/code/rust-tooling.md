---
description: 'Use for Rust linting, formatting, type checking, test coverage, and project validation. Covers clippy, rustfmt, cargo check, and tarpaulin.'
---

# Rust Tooling

Comprehensive guide to Rust linting, formatting, type checking, and coverage.

## Type Checking: cargo check

Rust's compiler IS the type checker. Fast check without building:

```bash
# Check without building
cargo check

# Check all targets (including tests, examples)
cargo check --all-targets

# Check with all features
cargo check --all-features
```

## Linting: Clippy

### Installation

Comes with rustup:

```bash
rustup component add clippy
```

### Configuration

```toml
# Cargo.toml
[lints.clippy]
pedantic = "warn"
nursery = "warn"

# Specific overrides
missing_errors_doc = "allow"
missing_panics_doc = "allow"
module_name_repetitions = "allow"
```

Or in code:

```rust
// lib.rs or main.rs
#![warn(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]
```

### Commands

```bash
# Check
cargo clippy

# Check all targets
cargo clippy --all-targets --all-features

# Fix (where possible)
cargo clippy --fix

# Treat warnings as errors (CI)
cargo clippy -- -D warnings
```

### Lint Categories

| Category | Flag | Description |
|----------|------|-------------|
| Default | (none) | Common issues |
| Pedantic | `clippy::pedantic` | Stricter, opinionated |
| Nursery | `clippy::nursery` | Experimental lints |
| Restriction | `clippy::restriction` | Very strict |

## Formatting: rustfmt

### Installation

```bash
rustup component add rustfmt
```

### Configuration

```toml
# rustfmt.toml
edition = "2021"
max_width = 100
tab_spaces = 4
use_small_heuristics = "Default"
imports_granularity = "Module"
group_imports = "StdExternalCrate"
reorder_imports = true
```

### Commands

```bash
# Format all
cargo fmt

# Check without modifying (CI)
cargo fmt -- --check

# Format specific file
rustfmt src/lib.rs
```

## Test Coverage: tarpaulin

### Installation

```bash
cargo install cargo-tarpaulin
```

### Commands

```bash
# Generate HTML report
cargo tarpaulin --out Html

# Generate XML for CI
cargo tarpaulin --out Xml
```

### Alternative: llvm-cov

```bash
cargo install cargo-llvm-cov
cargo llvm-cov --html
```

## Project Validation

Run all checks:

```bash
# Format check + Lint + Tests
cargo fmt -- --check && cargo clippy -- -D warnings && cargo test

# With all features
cargo fmt -- --check && \
cargo clippy --all-targets --all-features -- -D warnings && \
cargo test --all-features
```

## Recommended Cargo.toml Lints

```toml
[lints.rust]
unsafe_code = "forbid"

[lints.clippy]
pedantic = "warn"
nursery = "warn"
missing_errors_doc = "allow"
missing_panics_doc = "allow"
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

### With Coverage

```yaml
      - name: Install tarpaulin
        run: cargo install cargo-tarpaulin

      - name: Coverage
        run: cargo tarpaulin --out Xml

      - uses: codecov/codecov-action@v4
```

## Pre-commit Hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
cargo fmt -- --check || exit 1
cargo clippy -- -D warnings || exit 1
cargo test || exit 1
```

## Quick Reference

| Operation | Command |
|-----------|---------|
| Type check | `cargo check` |
| Lint check | `cargo clippy` |
| Lint fix | `cargo clippy --fix` |
| Format check | `cargo fmt -- --check` |
| Format fix | `cargo fmt` |
| Test | `cargo test` |
| Coverage | `cargo tarpaulin --out Html` |
| All checks | `cargo fmt -- --check && cargo clippy -- -D warnings && cargo test` |
| All fixes | `cargo fmt && cargo clippy --fix --allow-dirty` |

## Documentation

```bash
# Build docs
cargo doc

# Build and open
cargo doc --open

# Include private items
cargo doc --document-private-items
```
