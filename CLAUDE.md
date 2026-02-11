# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personality is a voice synthesis engine with a "cartridge" system for managing personas. It uses Piper TTS for text-to-speech and exposes functionality via CLI, MCP server, and Claude Code slash commands.

## Development Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run psn --help
uv run psn speak "Hello world"
uv run psn carts
uv run psn voices

# Start MCP server (stdio transport)
uv run psn mcp

# Install slash commands to ~/.claude/commands/psn/
uv run psn install

# Lint
uv run ruff check src/
uv run ruff format --check src/

# Test
uv run pytest
uv run pytest tests/test_config.py -v        # single file
uv run pytest -k "test_returns_voice"        # by name pattern
```

## Code Standards

### Limits
- **File size**: 150 lines preferred, 250 max
- **Function size**: 15 lines preferred, 30 max
- **Parameters**: 5 max per function

### Zero Tolerance
Never use - fix actual issues instead:
- `# noqa`, `# type: ignore`
- `_param` to suppress unused warnings
- Any linter suppression comments

### Exception Handling
- Always log or re-raise with context
- Use exception chaining (`raise ... from e`)
- Never silently swallow exceptions

### Logging
- Required for all modules
- Use appropriate levels (debug, info, warning, error)

### Testing
- **Minimum coverage: 91%** - Stop and add tests if coverage drops
- **Test as you go** - Write unit → Write test → Repeat
- **No test debt** - Tests are part of implementation
- Organization: `src/foo.py` → `tests/test_foo.py`

### Before Finishing
```bash
uv run ruff check src/    # Zero warnings
uv run ruff format src/
uv run pytest --cov       # Coverage ≥91%
```

## Architecture

### Core Components

- **`cli.py`** - Click CLI with commands: `speak`, `carts`, `voices`, `mcp`, `install`, `uninstall`
- **`speak.py`** - `Speak` class wrapping Piper TTS with voice caching and multi-player support (ffplay/afplay/aplay)
- **`config.py`** - Cart and voice configuration from `~/.config/personality/`

### MCP Server (`mcp/`)

Modular FastMCP-based server:

| File | Purpose |
|------|---------|
| `server.py` | Server setup, `AppContext` lifespan, `run_server()` entry point |
| `tools.py` | MCP tool: `speak(text, voice?)` |
| `resources.py` | MCP resources for cart data |
| `prompts.py` | MCP prompt templates |

**Exposed interfaces:**
- **Tool**: `speak(text, voice?)` - synthesize and play audio
- **Resources**: `personality://cart`, `personality://cart/{name}`, `personality://carts`
- **Prompt**: `speak(text)` - generate speak command template

The server uses lifespan context (`AppContext`) to hold active cart state. Cart is selected via `PERSONALITY_CART` env var (default: `bt7274`).

### Slash Commands (`commands/`)

Markdown templates installed to `~/.claude/commands/psn/` via `psn install`:
- `speak.md`, `cart.md`, `carts.md`, `voices.md`, `status.md`

### Configuration Layout

```
~/.config/personality/
├── carts/          # Personality carts (*.yml)
│   └── bt7274.yml
└── voices/         # Piper voice models (*.onnx + *.onnx.json)
    └── bt7274.onnx
```

### Cart Format

```yaml
preferences:
  identity:
    name: "BT-7274"
    tagline: "Protocol 3: Protect the Pilot"
  speak:
    voice: "bt7274"  # or legacy 'tts' key
memories:
  - subject: "protocols"
    content: ["Protocol 1", "Protocol 2", "Protocol 3"]
```

## Claude Code Integration

The package functions as a Claude Code plugin via `.claude-plugin/` and `.mcp.json`. After `psn install`, slash commands are available:
- `/psn:speak` - Speak text via MCP
- `/psn:cart` - Show/switch active cart
- `/psn:carts` - List available carts
- `/psn:voices` - List voice models
- `/psn:status` - Show configuration status
