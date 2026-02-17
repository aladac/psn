---
description: 'Use when writing Rust tests, setting up test modules, creating mocks, or implementing test patterns in Rust.'
---

# Rust Testing

Comprehensive guide to testing in Rust.

## Unit Tests (Same File)

```rust
// src/order.rs
pub struct Order {
    items: Vec<Item>,
    discount: Option<Decimal>,
}

impl Order {
    pub fn total(&self) -> Decimal {
        let subtotal: Decimal = self.items.iter().map(|i| i.price).sum();
        match self.discount {
            Some(d) => subtotal * (Decimal::ONE - d),
            None => subtotal,
        }
    }

    pub fn apply_discount(&mut self, percent: u8) -> Result<(), OrderError> {
        if percent > 100 {
            return Err(OrderError::InvalidDiscount);
        }
        self.discount = Some(Decimal::from(percent) / Decimal::from(100));
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_order() -> Order {
        Order {
            items: vec![Item { price: Decimal::from(100) }],
            discount: None,
        }
    }

    #[test]
    fn total_sums_item_prices() {
        let order = sample_order();
        assert_eq!(order.total(), Decimal::from(100));
    }

    #[test]
    fn apply_discount_reduces_total() {
        let mut order = sample_order();
        order.apply_discount(10).unwrap();
        assert_eq!(order.total(), Decimal::from(90));
    }

    #[test]
    fn apply_discount_rejects_invalid_percentage() {
        let mut order = sample_order();
        let result = order.apply_discount(150);
        assert!(matches!(result, Err(OrderError::InvalidDiscount)));
    }
}
```

## Integration Tests (Separate Directory)

```rust
// tests/integration_test.rs
use myapp::Order;

#[test]
fn order_workflow() {
    let mut order = Order::new();
    order.add_item(Item::new("Widget", 50));
    order.add_item(Item::new("Gadget", 75));

    assert_eq!(order.total(), 125);

    order.apply_discount(10).unwrap();
    assert_eq!(order.total(), 112.50);
}
```

## Test Organization

```
src/
├── lib.rs
├── order.rs          # Contains #[cfg(test)] mod tests
└── user.rs           # Contains #[cfg(test)] mod tests

tests/
├── common/
│   └── mod.rs        # Shared test utilities
├── order_test.rs     # Integration tests
└── user_test.rs
```

## Shared Test Utilities

```rust
// tests/common/mod.rs
use myapp::{Order, Item};

pub fn sample_order() -> Order {
    Order {
        items: vec![Item::new("Widget", 100)],
        discount: None,
    }
}

// tests/order_test.rs
mod common;

#[test]
fn test_order() {
    let order = common::sample_order();
    // ...
}
```

## Test Attributes

```rust
#[test]
fn basic_test() {
    assert!(true);
}

#[test]
#[ignore]  // Skip unless explicitly run
fn slow_test() {
    std::thread::sleep(Duration::from_secs(10));
}

#[test]
#[should_panic(expected = "out of range")]
fn panics_on_invalid_input() {
    validate(-1);
}
```

## Assertions

```rust
assert!(condition);
assert!(condition, "custom message");
assert_eq!(left, right);
assert_ne!(left, right);

// Pattern matching
assert!(matches!(result, Ok(_)));
assert!(matches!(result, Err(Error::NotFound { .. })));
assert!(matches!(value, Some(x) if x > 10));
```

## Async Tests

```rust
#[tokio::test]
async fn async_test() {
    let result = fetch_data().await;
    assert!(result.is_ok());
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn multi_threaded_test() {
    // Runs on multi-threaded runtime
}
```

## Mocking with mockall

```rust
use mockall::{automock, predicate::*};

#[automock]
trait Database {
    fn get_user(&self, id: u64) -> Option<User>;
    fn save_user(&self, user: &User) -> Result<(), DbError>;
}

#[test]
fn service_uses_database() {
    let mut mock_db = MockDatabase::new();

    mock_db
        .expect_get_user()
        .with(eq(42))
        .times(1)
        .returning(|_| Some(User { id: 42, name: "Alice".into() }));

    let service = UserService::new(mock_db);
    let user = service.find(42);

    assert_eq!(user.unwrap().name, "Alice");
}
```

## Property-Based Testing with proptest

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn parse_roundtrip(s in "[a-z]+") {
        let parsed = parse(&s).unwrap();
        let serialized = serialize(&parsed);
        prop_assert_eq!(s, serialized);
    }
}
```

## Commands

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_name

# Run tests in specific module
cargo test order::tests

# Run ignored tests
cargo test -- --ignored

# Show output from passing tests
cargo test -- --nocapture

# Run single-threaded
cargo test -- --test-threads=1

# Run only doc tests
cargo test --doc

# Run only integration tests
cargo test --test integration_test
```

## Code Coverage

```bash
# With cargo-tarpaulin
cargo install cargo-tarpaulin
cargo tarpaulin --out Html

# With llvm-cov
cargo install cargo-llvm-cov
cargo llvm-cov --html
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
- name: Test
  run: cargo test --all-features

- name: Coverage
  run: |
    cargo install cargo-tarpaulin
    cargo tarpaulin --out Xml
```

## Summary

| Command | Purpose |
|---------|---------|
| `cargo test` | Run all tests |
| `cargo test name` | Run tests matching name |
| `cargo test -- --ignored` | Run ignored tests |
| `cargo test -- --nocapture` | Show println! output |
| `cargo tarpaulin` | Code coverage |
