---
description: 'Use when writing TypeScript code, implementing TypeScript features, or needing TypeScript best practices and idioms.'
---

# TypeScript Coding Practices

Modern TypeScript idioms focused on type safety and readability.

## Strict Mode (Non-Negotiable)

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "exactOptionalPropertyTypes": true,
    "noPropertyAccessFromIndexSignature": true
  }
}
```

## Discriminated Unions

### State Modeling

```typescript
type RequestState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

function render(state: RequestState<User>) {
  switch (state.status) {
    case 'idle': return <Placeholder />;
    case 'loading': return <Spinner />;
    case 'success': return <UserCard user={state.data} />;
    case 'error': return <ErrorMessage error={state.error} />;
  }
}
```

## Const Assertions

```typescript
const roles = ['admin', 'user', 'guest'] as const;
type Role = (typeof roles)[number]; // 'admin' | 'user' | 'guest'
```

## Type Guards

```typescript
function isAdmin(person: User | Admin): person is Admin {
  return person.type === 'admin';
}

// Assertion Functions
function assertIsString(value: unknown): asserts value is string {
  if (typeof value !== 'string') {
    throw new Error(`Expected string, got ${typeof value}`);
  }
}
```

## Zod for Runtime Validation

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1).max(100),
  role: z.enum(['admin', 'user', 'guest']),
});

type User = z.infer<typeof UserSchema>;

// Parsing
function parseUser(data: unknown): User {
  return UserSchema.parse(data);
}
```

## Utility Types

```typescript
type UserUpdate = Partial<User>;
type UserPreview = Pick<User, 'id' | 'name'>;
type PublicUser = Omit<User, 'password'>;
type ImmutableUser = Readonly<User>;
type UserById = Record<string, User>;
```

## Avoid `any`

```typescript
// Bad: any disables type checking
function parse(json: string): any { ... }

// Better: unknown requires narrowing
function parse(json: string): unknown { ... }

// Best: validate into known type
function parseUser(json: string): User {
  const data = JSON.parse(json);
  return UserSchema.parse(data);
}
```

## Result Type Pattern

```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function divide(a: number, b: number): Result<number, string> {
  if (b === 0) {
    return { ok: false, error: 'Division by zero' };
  }
  return { ok: true, value: a / b };
}
```

## Type-Only Imports

```typescript
import type { User, Order } from './models';
import { createUser } from './services';
```

## Barrel Exports

```typescript
// lib/models/index.ts
export { User, type UserCreate } from './user';
export { Order, type OrderItem } from './order';
```

## Class Patterns

```typescript
class Order {
  private constructor(
    public readonly id: string,
    public readonly items: OrderItem[],
  ) {}

  static create(items: OrderItem[]): Order {
    return new Order(crypto.randomUUID(), items);
  }

  static fromJson(data: unknown): Order {
    const parsed = OrderSchema.parse(data);
    return new Order(parsed.id, parsed.items);
  }
}
```
