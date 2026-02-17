---
description: 'Use when writing TypeScript tests, setting up Vitest or Jest, creating mocks, or implementing test patterns in TypeScript.'
---

# TypeScript Testing

Comprehensive guide to testing TypeScript with Vitest.

## Installation

```bash
npm install -D vitest @vitest/coverage-v8
```

## Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node', // or 'jsdom' for browser
    include: ['src/**/*.test.ts', 'src/**/*.spec.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'dist/', '**/*.d.ts'],
    },
    testTimeout: 10000,
  },
});
```

## Structure (Readable First)

```typescript
// src/order/order.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { Order, OrderItem } from './order';

describe('Order', () => {
  describe('applyDiscount', () => {
    let order: Order;

    beforeEach(() => {
      order = new Order([new OrderItem({ price: 100 })]);
    });

    it('reduces total by percentage', () => {
      order.applyDiscount(10);
      expect(order.total).toBe(90);
    });

    it('does not modify total below threshold', () => {
      const smallOrder = new Order([new OrderItem({ price: 50 })]);
      smallOrder.applyDiscount(10);
      expect(smallOrder.total).toBe(50);
    });

    it('throws for negative percentage', () => {
      expect(() => order.applyDiscount(-5)).toThrowError(/positive/);
    });
  });
});
```

## Test Doubles

```typescript
import { describe, it, expect, vi } from 'vitest';

describe('OrderService', () => {
  it('sends notification on completion', () => {
    const notifier = {
      send: vi.fn(),
    };
    const service = new OrderService(notifier);

    service.completeOrder(123);

    expect(notifier.send).toHaveBeenCalledWith({
      userId: expect.any(Number),
      message: expect.stringContaining('123'),
    });
  });

  it('handles API failure gracefully', async () => {
    const api = {
      fetch: vi.fn().mockRejectedValue(new Error('Network down')),
    };
    const service = new UserService(api);

    const result = await service.getUser(1);

    expect(result).toBeNull();
  });
});
```

## Parametrized Tests

```typescript
import { describe, it, expect } from 'vitest';

describe('applyDiscount', () => {
  it.each([
    { discount: 0, expected: 100 },
    { discount: 10, expected: 90 },
    { discount: 50, expected: 50 },
    { discount: 100, expected: 0 },
  ])('applies $discount% discount correctly', ({ discount, expected }) => {
    const order = new Order([new OrderItem({ price: 100 })]);

    order.applyDiscount(discount);

    expect(order.total).toBe(expected);
  });
});
```

## Async Tests

```typescript
it('fetches user data', async () => {
  const user = await fetchUser(1);

  expect(user).toMatchObject({
    id: 1,
    name: expect.any(String),
  });
});
```

## Mocking Modules

```typescript
import { vi } from 'vitest';

vi.mock('./api', () => ({
  fetchUser: vi.fn().mockResolvedValue({ id: 1, name: 'Alice' }),
}));

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});
```

## Commands

```bash
# Run all tests
npx vitest

# Watch mode
npx vitest --watch

# Run specific file
npx vitest order.test.ts

# Run with coverage
npx vitest --coverage

# UI mode
npx vitest --ui
```

## Jest (Alternative)

```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/*.test.ts', '**/*.spec.ts'],
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.d.ts'],
};
```

## Co-located Tests

```
src/
├── users/
│   ├── index.ts
│   ├── user.ts
│   └── user.test.ts   # Co-located test
├── orders/
│   ├── index.ts
│   ├── order.ts
│   └── order.test.ts
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
- name: Test
  run: npx vitest --coverage

- name: Upload coverage
  uses: codecov/codecov-action@v4
```

## package.json Scripts

```json
{
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:watch": "vitest --watch"
  }
}
```

## Summary

| Command | Purpose |
|---------|---------|
| `npx vitest` | Run all tests |
| `npx vitest --watch` | Watch mode |
| `npx vitest --coverage` | With coverage |
| `npx vitest --ui` | UI mode |
| `npx vitest file.test.ts` | Run specific file |
