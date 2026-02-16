# Personality Plugin

Infrastructure layer for Claude Code providing persistent memory, semantic search, and local service integration.

## Features

| Category | Components |
|----------|------------|
| **Docker** | Local (ARM/fuji) and remote (AMD/junkpile) container management |
| **Ollama** | Embeddings and inference via junkpile |
| **PostgreSQL** | Vector storage with pgvector on junkpile |
| **SQLite** | Local vector storage with sqlite-vec |
| **Memory** | Persistent memory via embeddings |
| **Indexer** | Code and document semantic search |
| **TTS** | Text-to-speech via piper-tts |

## Architecture

```
fuji (local/ARM)          junkpile (remote/AMD)
├── Docker local          ├── Docker remote
├── SQLite                ├── Ollama
├── TTS (piper)           ├── PostgreSQL + pgvector
└── Indexer client        └── Memory storage
```

## Installation

### Prerequisites

**Local (fuji)**:
- Python 3.11+
- Docker
- piper-tts (`brew install piper`)
- SSH access to junkpile

**Remote (junkpile)**:
- Docker
- Ollama with nomic-embed-text
- PostgreSQL with pgvector extension

### Setup

```bash
# Install Python dependencies
cd /Users/chi/Projects/personality
pip install -e .

# Ensure SSH access
ssh junkpile "echo ok"

# Pull embedding model on junkpile
ssh junkpile "ollama pull nomic-embed-text"

# Create PostgreSQL database
ssh junkpile "createdb personality"
ssh junkpile "psql personality -c 'CREATE EXTENSION vector'"
```

### Enable Plugin

Add to `~/.claude/settings.json`:

```json
{
  "plugins": ["/Users/chi/Projects/personality"]
}
```

## Commands

| Command | Description |
|---------|-------------|
| `/session:save [name]` | Save current session state |
| `/session:restore <name>` | Restore a saved session |
| `/memory:store <subject> <content>` | Store in persistent memory |
| `/memory:recall <query>` | Recall by semantic search |
| `/memory:search [subject]` | Search or list memories |
| `/index:code [path]` | Index codebase for search |
| `/index:docs [path]` | Index documentation |
| `/index:status` | Show index statistics |

## MCP Tools

### docker-local / docker-remote
- `containers` - List containers
- `images` - List images
- `run` - Run container
- `stop` - Stop container
- `logs` - Get logs
- `exec` - Execute command

### ollama
- `embed` - Generate embeddings
- `generate` - Generate text
- `models` - List models
- `pull` - Download model

### postgres
- `query` - SELECT queries
- `execute` - Modifying statements
- `vector_search` - pgvector similarity search
- `schema` - Schema info

### sqlite
- `query` - SELECT queries
- `execute` - Modifying statements
- `vector_search` - sqlite-vec similarity search
- `tables` - List tables

### memory
- `store` - Store with embedding
- `recall` - Semantic recall
- `search` - Subject search
- `forget` - Delete memory
- `list` - List subjects

### indexer
- `index_code` - Index source files
- `index_docs` - Index documentation
- `search` - Semantic search
- `status` - Index statistics
- `clear` - Clear index

### tts
- `speak` - Text to speech
- `voices` - List voices
- `set_voice` - Change voice

## Skills

- **Memory Patterns**: Guidance for effective memory usage
- **Code Analysis**: Semantic code search patterns

## Agents

- **memory-curator**: Organize and clean up memories
- **code-analyzer**: Deep codebase analysis

## Hooks

All 9 Claude Code hooks have Python stubs ready for customization:
- PreToolUse, PostToolUse
- Stop, SubagentStop
- SessionStart, SessionEnd
- UserPromptSubmit
- PreCompact
- Notification

## Development

```bash
# Run tests
pytest

# Type check
mypy servers/

# Format
ruff format .
ruff check .
```

## License

Private - chi@tengu.host
