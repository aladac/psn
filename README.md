# psn

Persona system for Claude Code — cartridges, MCP server, memory, and TTS.

## Installation

```bash
pip install psn
```

## Quick Start

```bash
# Create a persona cartridge from training data
psn cart create bt7274

# Switch to the persona
psn cart switch bt7274

# List MCP resources
psn mcp resources

# Read persona identity
psn mcp read persona://current/identity
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `psn cart list` | List installed cartridges |
| `psn cart create <name>` | Create cartridge from training |
| `psn cart switch <name>` | Switch active persona |
| `psn cart show [name]` | Show cartridge details |
| `psn persona list` | List training files |
| `psn persona show <name>` | Show persona training data |
| `psn tts speak <text>` | Speak text with persona voice |
| `psn tts stop` | Stop current TTS playback |
| `psn tts voices` | List available voices |
| `psn mcp serve` | Run MCP server (stdio) |
| `psn mcp resources` | List MCP resources |
| `psn mcp read <uri>` | Read a resource |
| `psn mcp prompts` | List MCP prompts |
| `psn mcp prompt <name> [args]` | Execute a prompt |
| `psn memory list` | List stored memories |
| `psn knowledge add <s> <p> <o>` | Add knowledge triple |
| `psn knowledge query` | Query knowledge graph |
| `psn decision record <title>` | Record a decision |

## MCP Resources

| URI | Description |
|-----|-------------|
| `persona://current/memories` | Active persona's memories |
| `persona://current/identity` | Identity (name, type, tagline) |
| `persona://current/cart` | Full cartridge details |
| `persona://current/project` | Current project info |
| `persona://user` | User info (uid, groups, name) |
| `persona://host` | Host info (uname, uptime) |
| `knowledge://triples` | Knowledge graph triples |

## MCP Prompts

| Prompt | Arguments | Description |
|--------|-----------|-------------|
| `persona-greeting` | `user_name?` | In-character greeting |
| `in-character` | `question*` | Respond as persona |
| `remember` | `subject*`, `content*` | Store a memory |
| `knowledge-query` | `query*` | Query knowledge graph |

## Cartridge System

Personas are packaged as `.pcart` files (ZIP archives):

```
persona.pcart
├── persona.yml      # Memories and traits
├── preferences.yml  # Identity, TTS settings
└── manifest.yml     # Version, metadata
```

### Training Files

Training data lives in `training/*.yml`:

```yaml
name: BT-7274
type: Vanguard-class Titan
tagline: "Trust me."

memories:
  - subject: self.identity.name
    content: You are BT-7274, a Vanguard-class Titan.
  - subject: self.trait.loyalty
    content: You are fiercely loyal to your Pilot.
```

## Claude Code Plugin

As a Claude Code plugin, psn provides:

- **SessionStart hook**: Injects persona context
- **Stop hook**: Cancels TTS on interrupt
- **PreCompact hook**: Saves memory before compaction
- **MCP server**: Resources and prompts

### Enable Plugin

Add to `~/.claude/settings.json`:

```json
{
  "plugins": ["/path/to/psn"]
}
```

## Features

| Feature | Description |
|---------|-------------|
| **Cartridges** | Portable persona packages |
| **Persona Builder** | Generates LLM instructions from memories |
| **TTS** | piper-tts with per-persona voices |
| **Knowledge Graph** | Subject-predicate-object triples |
| **Decision Tracking** | ADR-style decision records |
| **Memory Management** | Extraction, consolidation, pruning |
| **MCP Server** | Resources and prompts for Claude Code |

## Development

```bash
# Clone
git clone https://github.com/aladac/psn
cd psn

# Install editable
pip install -e .

# Lint
ruff check src/
ruff format src/

# Test
pytest
```

## License

MIT
