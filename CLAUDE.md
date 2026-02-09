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

- **File size**: 150 lines preferred, 250 max
- **Function size**: 15 lines preferred, 30 max
- **No suppression comments**: Never use `# noqa`, `# type: ignore`
- **Exception handling**: Always log or re-raise with context
- **Logging**: Required for all modules (already configured)

## Architecture

### Core Components

- **`cli.py`** - Click CLI with commands: `speak`, `carts`, `voices`, `mcp`, `install`, `uninstall`
- **`speak.py`** - `Speak` class wrapping Piper TTS with voice caching and multi-player support (ffplay/afplay/aplay)
- **`config.py`** - Cart and voice configuration from `~/.config/personality/`

### MCP Server (`mcp/`)

FastMCP-based server exposing:
- **Tool**: `speak(text, voice?)` - synthesize and play audio
- **Resources**: `personality://cart`, `personality://cart/{name}`, `personality://carts`
- **Prompt**: `speak(text)` - generate speak command template

The server uses lifespan context (`AppContext`) to hold active cart state. Cart is selected via `PERSONALITY_CART` env var (default: `bt7274`).

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
