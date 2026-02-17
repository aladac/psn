---
description: 'Use to validate a TypeScript project by running all checks: tsc, ESLint, Prettier, and Vitest. Ensures project is CI-ready.'
---

# TypeScript Project Validation

Full validation workflow for TypeScript projects.

## Quick Validation

```bash
# Full validation (typecheck + lint + format + test)
npx tsc --noEmit && npx eslint src/ && npx prettier --check src/ && npx vitest run

# With Biome (alternative)
npx tsc --noEmit && npx biome check src/ && npx vitest run
```

## Validation Steps

### 1. Type Check

```bash
npx tsc --noEmit
```

### 2. Lint Check (ESLint)

```bash
npx eslint src/
```

**Fix issues:**
```bash
npx eslint --fix src/
```

### 3. Format Check (Prettier)

```bash
npx prettier --check src/
```

**Fix issues:**
```bash
npx prettier --write src/
```

### 4. Run Tests

```bash
# Full test suite
npx vitest run

# With coverage
npx vitest run --coverage

# Watch mode
npx vitest
```

## Biome Alternative

All-in-one lint + format:

```bash
# Check all
npx biome check src/

# Fix all
npx biome check --apply src/
```

## package.json Scripts

```json
{
  "scripts": {
    "build": "tsc",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src/",
    "lint:fix": "eslint --fix src/",
    "format": "prettier --write src/",
    "format:check": "prettier --check src/",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "validate": "npm run typecheck && npm run lint && npm run format:check && npm run test",
    "fix": "npm run lint:fix && npm run format"
  }
}
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

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Type check
        run: npx tsc --noEmit

      - name: Lint
        run: npx eslint src/

      - name: Format check
        run: npx prettier --check src/

      - name: Test
        run: npx vitest run --coverage

      - uses: codecov/codecov-action@v4
```

## Pre-commit Hooks

```bash
npm install -D husky lint-staged
npx husky init
```

```json
// package.json
{
  "lint-staged": {
    "*.ts": ["eslint --fix", "prettier --write"],
    "*.{json,md}": "prettier --write"
  }
}
```

## Validation Checklist

| Check | Command | Fix |
|-------|---------|-----|
| Types | `tsc --noEmit` | Fix type errors |
| Lint | `eslint src/` | `eslint --fix src/` |
| Format | `prettier --check src/` | `prettier --write src/` |
| Tests | `vitest run` | Fix failing tests |
| Coverage | `vitest run --coverage` | Add tests |

## Common Issues

### Type errors
```bash
# Verbose output
npx tsc --noEmit --pretty

# Check specific file
npx tsc --noEmit src/problematic.ts
```

### ESLint violations
```bash
# See all issues
npx eslint src/

# Fix automatically
npx eslint --fix src/

# Disable for line
// eslint-disable-next-line @typescript-eslint/no-explicit-any
```

### Prettier issues
```bash
# Check what would change
npx prettier --check --write src/

# Fix all
npx prettier --write src/
```

### Test failures
```bash
# Run specific test file
npx vitest run src/foo.test.ts

# Run with verbose output
npx vitest run --reporter=verbose

# Update snapshots
npx vitest run -u
```

## bun Workflow

If using bun:

```bash
# Install
bun install

# Run commands
bun run typecheck
bun run lint
bun test
```

## pnpm Workflow

If using pnpm:

```bash
# Install
pnpm install

# Run commands
pnpm run typecheck
pnpm run lint
pnpm test
```
