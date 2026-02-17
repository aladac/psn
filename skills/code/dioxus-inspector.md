---
description: 'Use when setting up or using dioxus-inspector for MCP-based debugging of Dioxus Desktop applications, connecting Claude Code to running Dioxus apps, or troubleshooting inspector connectivity.'
---

# Dioxus Inspector Integration

Enable Claude Code to debug Dioxus Desktop apps via MCP.

## Tools Reference

| MCP Tool | Purpose |
|----------|---------|
| `mcp__dioxus__status` | Check app connection, PID, uptime |
| `mcp__dioxus__get_dom` | Get simplified DOM tree |
| `mcp__dioxus__query_text` | Get text content by selector |
| `mcp__dioxus__query_html` | Get innerHTML by selector |
| `mcp__dioxus__query_all` | List elements matching selector |
| `mcp__dioxus__click` | Click element by selector |
| `mcp__dioxus__type_text` | Type into input field |
| `mcp__dioxus__eval` | Execute JavaScript in webview |
| `mcp__dioxus__inspect` | Analyze element visibility |
| `mcp__dioxus__diagnose` | Quick UI health check |
| `mcp__dioxus__screenshot` | Capture window (macOS) |
| `mcp__dioxus__resize` | Resize window |
| `mcp__dioxus__dom_to_rsx` | Convert HTML to RSX |
| `mcp__dioxus__doctor` | Run dx doctor |
| `mcp__dioxus__check` | Run dx check |

## Quick Setup

### 1. Add Dependency

```toml
# Cargo.toml
[features]
desktop = ["dioxus/desktop", "dioxus-inspector"]

[dependencies]
dioxus-inspector = { version = "0.1.2", optional = true }
```

### 2. Embed Bridge

```rust
#[cfg(feature = "desktop")]
use dioxus_inspector::{start_bridge, EvalResponse};

#[cfg(feature = "desktop")]
const INSPECTOR_PORT: u16 = 9999;

fn app() -> Element {
    #[cfg(feature = "desktop")]
    use_effect(|| {
        let mut eval_rx = start_bridge(INSPECTOR_PORT, "my-app");
        spawn(async move {
            while let Some(cmd) = eval_rx.recv().await {
                let response = match document::eval(&cmd.script).await {
                    Ok(val) => EvalResponse::success(val.to_string()),
                    Err(e) => EvalResponse::error(e.to_string()),
                };
                let _ = cmd.response_tx.send(response);
            }
        });
    });

    rsx! { /* ... */ }
}
```

### 3. Configure MCP

```json
// .mcp.json in project root
{
  "mcpServers": {
    "dioxus": {
      "command": "dioxus-mcp",
      "env": { "DIOXUS_BRIDGE_URL": "http://127.0.0.1:9999" }
    }
  }
}
```

### 4. Restart Claude Code

After adding `.mcp.json`, restart Claude Code to load the MCP server.

## Verification

```bash
# Start your app
dx serve --features desktop

# Test bridge is running
curl http://127.0.0.1:9999/status
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No response from `/status` | App not running or bridge not embedded |
| MCP tools not available | Restart Claude Code after adding `.mcp.json` |
| Port already in use | Change `INSPECTOR_PORT` and update `.mcp.json` |
| Eval returns errors | Check JavaScript syntax in webview context |

## Related Skills

- `psn:code:rust-dioxus` - Dioxus development patterns
- `psn:code:dioxus-debug` - Debugging workflows with inspector
