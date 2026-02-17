---
description: 'Use when writing Rust code, implementing Rust features, or needing Rust best practices and idioms.'
---

# Tools Reference

## Built-in Tools
| Tool | Purpose |
|------|---------|
| `Read` | Read .rs files |
| `Write` | Create new Rust files |
| `Edit` | Modify Rust code |
| `Bash` | Run `cargo`, `rustc`, `clippy`, `rustfmt` |
| `Glob` | Find Rust files (*.rs) |
| `Grep` | Search Rust code |

## Related Skills
- `psn:code:rust-cli` - Clap CLI development
- `psn:code:rust-test` - Rust testing
- `psn:code:rust-dioxus` - Dioxus GUI development
- `psn:code:rust-tooling` - Lint/format/typecheck
- `psn:code:rust-validate` - Full validation workflow

---

# Rust Coding Practices

Modern Rust idioms focused on safety, performance, and clarity.

## Parse, Don't Validate

Make invalid states unrepresentable via newtype wrappers:

```rust
pub struct Email(String);

impl Email {
    pub fn parse(s: &str) -> Result<Self, EmailError> {
        if s.contains('@') && s.contains('.') {
            Ok(Self(s.to_owned()))
        } else {
            Err(EmailError::InvalidFormat)
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

// Can't construct invalid Email
fn send_email(to: Email, subject: Subject) { ... }
```

## Error Handling

### Library Code: `thiserror`

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ParseError {
    #[error("invalid format: {0}")]
    InvalidFormat(String),

    #[error("missing field: {field}")]
    MissingField { field: &'static str },

    #[error(transparent)]
    Io(#[from] std::io::Error),
}
```

### Application Code: `anyhow`

```rust
use anyhow::{Context, Result};

fn load_config(path: &Path) -> Result<Config> {
    let contents = fs::read_to_string(path)
        .context("failed to read config file")?;

    let config: Config = toml::from_str(&contents)
        .context("failed to parse config")?;

    Ok(config)
}
```

## Builder Pattern

```rust
#[derive(Default)]
pub struct RequestBuilder {
    url: Option<String>,
    method: Method,
    headers: HashMap<String, String>,
}

impl RequestBuilder {
    pub fn new() -> Self { Self::default() }

    pub fn url(mut self, url: impl Into<String>) -> Self {
        self.url = Some(url.into());
        self
    }

    pub fn build(self) -> Result<Request, BuildError> {
        let url = self.url.ok_or(BuildError::MissingUrl)?;
        Ok(Request { url, method: self.method, headers: self.headers })
    }
}
```

## Iterators Over Loops

```rust
// Functional (prefer)
let results: Vec<_> = items
    .iter()
    .filter(|item| item.is_valid())
    .map(|item| item.process())
    .collect();

// Early exit with Iterator
let results: Result<Vec<_>, _> = items
    .iter()
    .map(|item| process(item))
    .collect(); // Stops on first Err
```

## Smart Pointers

```rust
// Box: single ownership, heap allocation
let data: Box<LargeStruct> = Box::new(large_struct);

// Arc: shared ownership, multi-thread
let shared: Arc<Config> = Arc::new(config);

// Mutex: interior mutability, multi-thread
let mutex: Mutex<Vec<i32>> = Mutex::new(vec![]);
```

## Module Organization

```rust
// lib.rs
pub mod config;      // Public module
mod internal;        // Private module

pub use config::Config;  // Re-export
```

### Prelude Pattern

```rust
// src/prelude.rs
pub use crate::config::Config;
pub use crate::error::{Error, Result};
```

## Flatten API Exports

```rust
// docker/mod.rs
mod client;    // private
pub use client::DockerClient;  // docker::DockerClient
```

## .unwrap() Policy

**Avoid in library code.** Use instead:
- `.unwrap_or(default)`
- `.unwrap_or_default()`
- `.expect("reason this can't fail")`
- `.ok_or(Error::Missing)?`

**Acceptable:**
- Tests
- After infallible operations: `Regex::new(r"^\d+$").unwrap()`

## Forbidden

Never commit:
- `dbg!()` - debug macro
- `todo!()` - unfinished code
- `panic!()` for recoverable errors
- `.unwrap()` on user input or external data
- `use foo::*` (except `use super::*` in tests)
