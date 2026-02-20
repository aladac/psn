---
description: 'Use for TypeScript linting, formatting, type checking, test coverage, and project validation. Covers ESLint, Prettier, Biome, tsc, and Vitest coverage.'
---

# TypeScript Tooling

Comprehensive guide to TypeScript linting, formatting, type checking, and coverage.

## Type Checking: TypeScript Compiler

### Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    // Strictness (non-negotiable)
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true,
    "noPropertyAccessFromIndexSignature": true,
    "noImplicitOverride": true,

    // Module resolution
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "resolveJsonModule": true,

    // Output
    "target": "ES2022",
    "outDir": "dist",
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Commands

```bash
# Type check only (no emit)
npx tsc --noEmit

# Build
npx tsc

# Watch mode
npx tsc --watch
```

## Linting: ESLint (Flat Config)

### Installation

```bash
npm install -D eslint @eslint/js typescript-eslint
```

### Configuration

```javascript
// eslint.config.js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
      '@typescript-eslint/explicit-function-return-type': 'off',
    },
  },
  {
    files: ['**/*.test.ts', '**/*.spec.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    ignores: ['dist/', 'node_modules/', 'coverage/'],
  }
);
```

### Commands

```bash
# Check
npx eslint src/

# Fix
npx eslint --fix src/
```

## Formatting: Prettier

### Installation

```bash
npm install -D prettier
```

### Configuration

```json
// .prettierrc
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 80,
  "tabWidth": 2
}
```

### Commands

```bash
# Check
npx prettier --check src/

# Fix
npx prettier --write src/
```

## All-in-One: Biome (Alternative)

Modern replacement for ESLint + Prettier:

### Installation

```bash
npm install -D @biomejs/biome
```

### Configuration

```json
// biome.json
{
  "$schema": "https://biomejs.dev/schemas/1.5.0/schema.json",
  "organizeImports": { "enabled": true },
  "linter": {
    "enabled": true,
    "rules": { "recommended": true }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "lineWidth": 80
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "single",
      "semicolons": "always"
    }
  }
}
```

### Commands

```bash
# Check all
npx biome check src/

# Fix all
npx biome check --apply src/
```

## Test Coverage: Vitest

### Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'dist/', '**/*.d.ts'],
    },
  },
});
```

### Commands

```bash
# Run with coverage
npx vitest --coverage

# Generate HTML report
npx vitest --coverage --reporter=html
```

## Project Validation

Run all checks:

```bash
# ESLint + Prettier
npx tsc --noEmit && npx eslint src/ && npx prettier --check src/ && npx vitest

# Biome
npx tsc --noEmit && npx biome check src/ && npx vitest
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
        run: npx vitest --coverage

      - uses: codecov/codecov-action@v4
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
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "check": "npm run typecheck && npm run lint && npm run test",
    "fix": "npm run lint:fix && npm run format"
  }
}
```

## Quick Reference

| Operation | ESLint + Prettier | Biome |
|-----------|-------------------|-------|
| Type check | `tsc --noEmit` | `tsc --noEmit` |
| Lint check | `eslint src/` | `biome lint src/` |
| Lint fix | `eslint --fix src/` | `biome check --apply src/` |
| Format check | `prettier --check src/` | `biome format --check src/` |
| Format fix | `prettier --write src/` | `biome format --write src/` |
| All checks | `npm run check` | `biome check src/` |
| All fixes | `npm run fix` | `biome check --apply src/` |

## Recommended Stack

- **Types**: TypeScript with `strict: true`
- **Lint**: ESLint with typescript-eslint (or Biome)
- **Format**: Prettier (or Biome)
- **Testing**: Vitest with v8 coverage
