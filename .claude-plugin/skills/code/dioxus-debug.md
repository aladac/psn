---
description: 'Use when debugging Dioxus Desktop applications using dioxus-inspector MCP tools, investigating UI issues, querying DOM state, or interacting with running Dioxus apps.'
---

# Debugging Dioxus Apps with Inspector

Workflows for debugging running Dioxus Desktop apps via MCP.

## Prerequisites

- dioxus-inspector embedded in app (see `psn:code:dioxus-inspector`)
- App running with desktop feature
- Claude Code restarted after MCP config

## Debugging Workflow

### 1. Check Connection

```
mcp__dioxus__status
```

Returns: app name, PID, uptime. If this fails, app isn't running or bridge isn't embedded.

### 2. Get DOM Overview

```
mcp__dioxus__get_dom
```

Returns simplified DOM tree. Use to understand current UI structure.

### 3. Query Specific Elements

```
# Get text content
mcp__dioxus__query_text { selector: ".header-title" }

# Get full HTML
mcp__dioxus__query_html { selector: "#main-content" }

# List all matching elements
mcp__dioxus__query_all { selector: "button" }
```

### 4. Inspect Visibility

```
mcp__dioxus__inspect { selector: ".modal" }
```

Returns visibility analysis: is element in viewport, dimensions, computed styles.

### 5. Quick Health Check

```
mcp__dioxus__diagnose
```

Runs automated checks for common UI issues.

## Interactive Debugging

### Click Elements

```
mcp__dioxus__click { selector: "#submit-button" }
```

### Type Into Inputs

```
mcp__dioxus__type_text { selector: "#search-input", text: "test query" }
```

### Execute JavaScript

```
mcp__dioxus__eval { script: "document.querySelector('.count').textContent" }
```

Use for:
- Reading computed values
- Triggering custom events
- Checking JavaScript state

## Visual Debugging

### Take Screenshot

```
mcp__dioxus__screenshot
```

Captures current window state. macOS only.

### Resize Window

```
mcp__dioxus__resize { width: 1280, height: 720 }
```

Test responsive layouts.

## RSX Conversion

### Convert HTML to RSX

```
mcp__dioxus__dom_to_rsx { html: "<div class=\"foo\">bar</div>" }
```

Uses `dx translate` under the hood.

## Build Diagnostics

### Check Environment

```
mcp__dioxus__doctor
```

Runs `dx doctor` to verify Dioxus toolchain.

### Validate Project

```
mcp__dioxus__check
```

Runs `dx check` for project issues.

## Common Patterns

### Debug State Changes

1. `mcp__dioxus__query_text` on state-displaying element
2. `mcp__dioxus__click` to trigger action
3. `mcp__dioxus__query_text` again to see change

### Find Hidden Elements

```
mcp__dioxus__query_all { selector: "[style*='display: none']" }
mcp__dioxus__query_all { selector: ".hidden" }
```

### Debug Event Handlers

```
mcp__dioxus__eval { script: "window.debugLastEvent" }
```

Add `window.debugLastEvent = evt` in your Dioxus event handlers to capture.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Selector returns empty | Element not rendered | Check conditional rendering logic |
| Click has no effect | Wrong selector or element disabled | Use `query_all` to verify element exists |
| Eval errors | JavaScript not valid in webview | Check browser compatibility |
| Screenshot blank | Window minimized or off-screen | Resize/reposition window |

## Related Skills

- `psn:code:dioxus-inspector` - Setup and configuration
- `psn:code:rust-dioxus` - Dioxus development patterns
