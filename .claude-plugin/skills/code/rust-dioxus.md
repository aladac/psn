---
description: 'Use when building Rust desktop GUI applications with Dioxus, implementing reactive UIs, or creating cross-platform desktop apps in Rust.'
---

# Rust GUI Development (Dioxus)

Best practices for Rust desktop applications using Dioxus.

## Project Structure

```
project/
├── Cargo.toml              # Workspace root
├── src/                    # Library crate (shared types, clients)
│   └── lib.rs
├── desktop/                # GUI crate (isolated)
│   ├── Cargo.toml
│   ├── Dioxus.toml         # Window settings, asset dir
│   ├── assets/
│   │   └── tailwind.css
│   └── src/
│       ├── main.rs         # Entry, global hooks
│       ├── state.rs        # All Signal<T> definitions
│       └── components/     # UI components
```

**Key Rule**: Desktop GUI is a separate crate. Share only types and clients.

## Dependencies

```toml
[dependencies]
dioxus = { version = "0.6", features = ["desktop"] }
dioxus-primitives = { git = "https://github.com/DioxusLabs/components" }
dioxus-free-icons = { version = "0.10", features = ["font-awesome-solid", "lucide"] }

[dev-dependencies]
dioxus-ssr = "0.6"
wiremock = "0.6"
```

## Primitives First

**Always use `dioxus-primitives` components.** Don't build custom versions.

| Need | Use |
|------|-----|
| Modal | `Dialog`, `DialogContent`, `DialogTitle` |
| Dropdown | `Popover`, `PopoverTrigger`, `PopoverContent` |
| Progress | `Progress`, `ProgressIndicator` |
| Tooltips | `Tooltip`, `TooltipTrigger`, `TooltipContent` |
| Toggle | `Switch`, `SwitchThumb` |

## State Management

### Global State with Signals

```rust
// state.rs
#[derive(Clone, Copy)]
pub struct AppState {
    pub items: Signal<Vec<Item>>,
    pub loading: Signal<bool>,
    pub error: Signal<Option<String>>,
    pub selected_ids: Signal<HashSet<String>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            items: Signal::new(vec![]),
            loading: Signal::new(false),
            error: Signal::new(None),
            selected_ids: Signal::new(HashSet::new()),
        }
    }
}
```

### Context Provider Pattern

```rust
// main.rs
fn app() -> Element {
    let state = use_context_provider(AppState::new);

    rsx! {
        Router::<Route> {}
    }
}

// Any child component
fn SomeComponent() -> Element {
    let mut state = use_context::<AppState>();
    // ...
}
```

### Signal Access Rules

```rust
// Reading
let items = state.items.read().clone();
let is_loading = *state.loading.read();

// Writing
state.items.set(new_items);

// Mutation (keep lock scope tight!)
{
    let mut items = state.items.write();
    items.insert(key, value);
}  // Lock released here
```

**Critical**: Never hold signal locks across `.await` points.

## Component Patterns

### Props Need Traits

```rust
// Props require: Clone + PartialEq + 'static
#[derive(Clone, PartialEq)]
pub struct ItemDisplay {
    pub id: String,
    pub name: String,
}
```

### Basic Component

```rust
#[component]
pub fn ItemCard(item: ItemDisplay) -> Element {
    rsx! {
        div { class: "card",
            h3 { "{item.name}" }
            p { "ID: {item.id}" }
        }
    }
}
```

### Component with Callbacks

```rust
#[component]
pub fn SearchBar(on_search: EventHandler<String>) -> Element {
    let mut query = use_signal(String::new);

    rsx! {
        input {
            value: "{query}",
            oninput: move |e| query.set(e.value()),
            onkeypress: move |e| {
                if e.key() == Key::Enter {
                    on_search.call(query.read().clone());
                }
            }
        }
    }
}

// Usage
SearchBar { on_search: move |q| handle_search(q) }
```

### Event Handler with Async

```rust
let handle_click = {
    let item = item.clone();  // Clone before move
    move |evt: MouseEvent| {
        evt.stop_propagation();
        spawn(async move {
            state.loading.set(true);
            match client.fetch(&item).await {
                Ok(data) => state.data.set(data),
                Err(e) => state.error.set(Some(e.to_string())),
            }
            state.loading.set(false);
        });
    }
};
```

### Conditional Rendering

```rust
rsx! {
    if *state.loading.read() {
        LoadingSpinner {}
    } else if let Some(err) = state.error.read().as_ref() {
        ErrorBanner { message: err.clone() }
    } else if state.items.read().is_empty() {
        EmptyState { message: "No items" }
    } else {
        for item in state.items.read().iter() {
            ItemCard { key: "{item.id}", item: item.clone() }
        }
    }
}
```

## Hooks

```rust
// use_hook - One-time initialization
use_hook(|| {
    spawn(async move {
        if let Ok(config) = Config::load() {
            state.config.set(Some(config));
        }
    });
});

// use_memo - Derived values
let filtered = use_memo(move || {
    state.items.read()
        .iter()
        .filter(|i| i.matches(&state.filter.read()))
        .cloned()
        .collect::<Vec<_>>()
});

// use_effect - React to changes
use_effect(move || {
    let query = state.search_query.read().clone();
    if query.len() >= 3 {
        spawn(async move { /* trigger search */ });
    }
});
```

## Async Patterns

```rust
// GOOD - Dioxus runtime integration
spawn(async move {
    let result = client.fetch().await;
    state.data.set(result);
});

// BAD - Outside Dioxus runtime
tokio::spawn(async move {
    state.data.set(result);  // Won't trigger UI update
});
```

## Critical Rules

1. **Signals are truth** - All mutable state through `Signal<T>`
2. **Scope locks tight** - `{ let x = signal.read(); }` then drop
3. **Clone before async** - `let item = item.clone(); move |_| spawn(...)`
4. **Spawn don't block** - Never `.await` in component render
5. **Key your lists** - `for item in items { Card { key: "{item.id}" } }`
6. **EventHandler for callbacks** - Parent-child via `EventHandler<T>`
7. **Context over props** - Shared state via `use_context`

## Forbidden

- `.await` in component body
- Holding signal locks across await
- `tokio::spawn` for UI updates
- Prop drilling beyond 2 levels
- Custom components when primitives exist

## Development

```bash
cd desktop && dx serve
```

## Summary

| Pattern | Use |
|---------|-----|
| Global state | `AppState` with `Signal<T>` fields |
| Component state | `use_signal()` |
| Derived state | `use_memo()` |
| Side effects | `use_effect()` |
| Async work | `spawn(async move { ... })` |
| Shared state | `use_context::<AppState>()` |
