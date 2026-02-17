---
description: 'Use for cross-language coding best practices, design patterns, and principles that apply to Ruby, Rust, Python, and TypeScript.'
---

# Common Coding Practices

Cross-language patterns that improve readability and maintainability.

## Guard Clauses & Early Returns

Exit early. Keep the happy path unindented.

```ruby
# Prefer: Guard clauses
def process(user)
  return unless user
  return if user.banned?
  raise ArgumentError, "No email" unless user.email

  # Happy path at base indentation
  send_notification(user)
end

# Avoid: Nested conditionals
def process(user)
  if user
    unless user.banned?
      if user.email
        send_notification(user)
      end
    end
  end
end
```

**Why**: The first reads top-to-bottom. The second requires mental stack management.

## Test File Mirroring

Test files mirror source structure exactly:

```
# Source                          # Test
lib/something/something_else.rb → spec/something/something_else_spec.rb
src/users/service.py             → tests/users/test_service.py
src/orders/validator.ts          → src/orders/validator.test.ts
src/parser/mod.rs                → src/parser/mod.rs (inline #[cfg(test)])
```

**Why**: One-to-one mapping = instant navigation. No hunting.

## Directory Structure Over Flat Files

Categorize by domain, not by type:

```
# Yes - domain-driven
src/
  users/
    models.py
    services.py
  orders/
    models.py
    services.py

# No - flat soup
src/
  user_models.py
  user_services.py
  order_models.py
```

**Why**: Domains scale independently. Flat files become unmanageable.

## Parse, Don't Validate

Make invalid states unrepresentable:

```rust
// Bad: stringly-typed
fn send_email(to: String) { ... }

// Good: validated at construction
struct Email(String);
impl Email {
    fn parse(s: &str) -> Result<Self, EmailError> { ... }
}
fn send_email(to: Email) { ... }  // Can't pass invalid email
```

Applies to all languages:
- **Ruby**: Value objects with validation in initializer
- **Python**: Pydantic models or `@dataclass` with `__post_init__`
- **TypeScript**: Branded types or Zod schemas
- **Rust**: Newtypes with `TryFrom`

## Error Handling at Boundaries

Handle errors where they enter your system:

```
┌─────────────────────────────────────────────┐
│              Your Application               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │ Service │→ │ Domain  │→ │ Service │     │
│  └────┬────┘  └─────────┘  └────┬────┘     │
│       │ VALIDATE HERE           │ HANDLE   │
└───────┼─────────────────────────┼──────────┘
    External                   External
```

**Why**: Core domain logic stays clean. Boundaries handle the messy real world.

## Prefer Explicit Over Magic

```python
# Magic: What does this do?
@auto_inject
@cache(ttl=300)
@retry(3)
def process(data): ...

# Explicit: Clear dependencies
def process(
    data: InputData,
    cache: Cache,
    logger: Logger,
    max_retries: int = 3,
) -> Result: ...
```

**When magic is okay**: Framework conventions (Rails, Django) where everyone knows the patterns.

## Composition Over Inheritance

Favor mixins and delegation over deep class hierarchies:

```ruby
# Prefer: Composition
class Dog
  include Walkable
  include Barkable
end

# Avoid: Deep inheritance
class Animal; end
class Mammal < Animal; end
class Canine < Mammal; end
class Dog < Canine; end
```

**Why**: Inheritance is rigid. Composition is flexible.

## The 7±2 Rule

Cognitive psychology tells us humans can hold **7±2 items** in working memory.

- If understanding a function requires tracking more than 7 things, it's too complex
- This is independent of line count—a 50-line function can be simple, a 10-line function complex

## Line Limits: Modern View

| Element | Classic | Modern | Guidance |
|---------|---------|--------|----------|
| Method/Function | 10 lines | No hard limit | Single responsibility |
| Class/Module | 100 lines | No hard limit | Single reason to change |
| File | 200-300 lines | No hard limit | One concept per file |
| Line width | 80 chars | 80-120 chars | Don't wrap mid-expression |

## Naming is Documentation

Names should reveal intent without requiring comments:

```python
# Vague
def process(d):
    return [x for x in d if x > 0]

# Clear
def filter_positive_values(numbers: list[int]) -> list[int]:
    return [n for n in numbers if n > 0]
```

## Comments Explain Why, Not What

```ruby
# Bad: restates code
# Increment counter by one
counter += 1

# Good: explains reasoning
# Rate limit requires 1-second gaps between API calls
sleep(1)
```

## Summary

| Practice | Why |
|----------|-----|
| Guard clauses | Reduces nesting, reads top-to-bottom |
| Test mirroring | Instant navigation |
| Directory structure | Scales with domain complexity |
| Parse don't validate | Invalid states unrepresentable |
| Boundary handling | Clean core, messy edges |
| Explicit over magic | Maintainability wins |
| Composition | Flexible over rigid |
| 7±2 rule | Respect cognitive limits |
