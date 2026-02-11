# FLOW.md

> **Integration flow for Personality + Memory + Claude Code hooks**
>
> **Constraint:** No external shell scripts. All hooks call `uv run psn <command>` directly.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Claude Code CLI                             │
├─────────────────────────────────────────────────────────────────────┤
│  Hooks (settings.json)                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │ SessionStart │ │ SessionEnd   │ │ Stop         │ │Notification│  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────┬──────┘  │
│         │                │                │               │         │
│         ▼                ▼                ▼               ▼         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    uv run psn <hook-cmd>                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  MCP Server (stdio)                                                 │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌───────────────┐   │
│  │  speak  │ │ remember │ │ recall │ │ forget │ │  consolidate  │   │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └───┬────┘ └───────┬───────┘   │
│       │          │           │          │              │           │
│       ▼          ▼           ▼          ▼              ▼           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      Personality Core                        │   │
│  │  ┌─────────┐  ┌─────────────┐  ┌────────────────────────┐    │   │
│  │  │  Speak  │  │ MemoryStore │  │        Cart            │    │   │
│  │  │ (Piper) │  │(sqlite-vec) │  │ (identity/preferences) │    │   │
│  │  └─────────┘  └──────┬──────┘  └────────────────────────┘    │   │
│  │                      │                                       │   │
│  │               ┌──────┴──────┐                                │   │
│  │               │  Embedder   │                                │   │
│  │               │  (Ollama)   │                                │   │
│  │               └─────────────┘                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hook Configuration

### settings.json

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "uv run psn hook session-start",
        "timeout": 5000
      }
    ],
    "SessionEnd": [
      {
        "command": "uv run psn hook session-end",
        "timeout": 10000
      }
    ],
    "Stop": [
      {
        "command": "uv run psn hook stop",
        "timeout": 3000
      }
    ],
    "Notification": [
      {
        "command": "uv run psn hook notify",
        "timeout": 3000
      }
    ]
  },
  "mcpServers": {
    "personality": {
      "command": "uv",
      "args": ["run", "psn", "mcp"],
      "cwd": "/Users/chi/Projects/personality",
      "env": {
        "PERSONALITY_CART": "bt7274"
      }
    }
  }
}
```

---

## Hook Commands

### CLI Hook Subcommand

```python
# src/personality/cli.py

@cli.group()
def hook():
    """Hook commands called by Claude Code."""
    pass


@hook.command("session-start")
@click.pass_context
def hook_session_start(ctx):
    """Initialize session: load cart, greet pilot."""
    cart = ctx.obj["cart"]
    speak = ctx.obj["speak"]
    memory = ctx.obj["memory"]

    # Load recent context
    recent = memory.recall("session.context", k=3)

    # Greet
    greeting = f"Neural link established. {cart.identity.tagline}"
    speak.say(greeting, cart.voice)

    # Output for Claude to see
    click.echo(json.dumps({
        "status": "initialized",
        "cart": cart.name,
        "recent_context": [m.content for m in recent],
    }))


@hook.command("session-end")
@click.pass_context
def hook_session_end(ctx):
    """End session: consolidate memories, farewell."""
    memory = ctx.obj["memory"]
    speak = ctx.obj["speak"]
    cart = ctx.obj["cart"]

    # Consolidate similar memories
    merged = memory.consolidate()

    # Farewell
    speak.say("Session complete. Standing by, Pilot.", cart.voice)

    click.echo(json.dumps({
        "status": "terminated",
        "memories_consolidated": merged,
    }))


@hook.command("stop")
@click.pass_context
def hook_stop(ctx):
    """Called when Claude stops generating."""
    # Read stop reason from stdin (Claude passes JSON)
    import sys
    data = json.load(sys.stdin)

    stop_reason = data.get("stop_reason", "unknown")

    # Only speak on end_turn, not tool_use
    if stop_reason == "end_turn":
        speak = ctx.obj["speak"]
        cart = ctx.obj["cart"]
        speak.say("Standing by.", cart.voice)


@hook.command("notify")
@click.option("--message", "-m", default="Task complete")
@click.pass_context
def hook_notify(ctx, message):
    """Speak notification."""
    speak = ctx.obj["speak"]
    cart = ctx.obj["cart"]
    speak.say(message, cart.voice)
```

---

## MCP Tools (Complete Set)

### Tool Definitions

```python
# src/personality/mcp/tools.py

from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("personality")


@mcp.tool()
def speak(text: str, voice: str | None = None, ctx: Context = None) -> str:
    """
    Speak text aloud using the configured personality voice.

    Args:
        text: Text to speak
        voice: Optional voice override (defaults to cart voice)
    """
    app = ctx.request_context.lifespan_context
    voice = voice or app.cart.voice
    app.speak.say(text, voice)
    return f"Spoke: {text[:50]}..."


@mcp.tool()
def remember(subject: str, content: str, ctx: Context = None) -> str:
    """
    Store a memory for later recall.

    Args:
        subject: Memory category (e.g., "user.preference.language")
        content: The information to remember
    """
    app = ctx.request_context.lifespan_context
    memory_id = app.memory.remember(subject, content)
    return f"Remembered [{subject}]: {content[:50]}... (id: {memory_id[:8]})"


@mcp.tool()
def recall(query: str, limit: int = 5, ctx: Context = None) -> list[dict]:
    """
    Recall memories relevant to a query using hybrid search.

    Args:
        query: Natural language query
        limit: Maximum number of memories to return
    """
    app = ctx.request_context.lifespan_context
    memories = app.memory.recall(query, k=limit)
    return [
        {
            "id": m.id,
            "subject": m.subject,
            "content": m.content,
            "relevance": round(1 - (m.distance or 0), 3),
        }
        for m in memories
    ]


@mcp.tool()
def forget(memory_id: str, ctx: Context = None) -> str:
    """
    Delete a specific memory by ID.

    Args:
        memory_id: The UUID of the memory to delete
    """
    app = ctx.request_context.lifespan_context
    if app.memory.forget(memory_id):
        return f"Memory {memory_id[:8]} deleted"
    return f"Memory {memory_id[:8]} not found"


@mcp.tool()
def consolidate(threshold: float = 0.85, ctx: Context = None) -> str:
    """
    Merge similar memories to reduce redundancy.

    Args:
        threshold: Similarity threshold (0.0-1.0) for merging
    """
    app = ctx.request_context.lifespan_context
    merged = app.memory.consolidate(similarity_threshold=threshold)
    return f"Consolidated {merged} duplicate memories"
```

---

## MCP Resources

### Resource Definitions

```python
# src/personality/mcp/resources.py

@mcp.resource("personality://cart")
def get_current_cart(ctx: Context) -> str:
    """Get current personality cart data."""
    app = ctx.request_context.lifespan_context
    return yaml.dump(app.cart.to_dict())


@mcp.resource("personality://cart/{name}")
def get_cart_by_name(name: str) -> str:
    """Get specific cart by name."""
    cart = Cart.load(name)
    return yaml.dump(cart.to_dict())


@mcp.resource("personality://memories")
def get_all_memories(ctx: Context) -> str:
    """Get all stored memories."""
    app = ctx.request_context.lifespan_context
    memories = app.memory.list_all()
    return json.dumps([m.__dict__ for m in memories])


@mcp.resource("personality://memories/{subject}")
def get_memories_by_subject(subject: str, ctx: Context) -> str:
    """Get memories matching a subject prefix."""
    app = ctx.request_context.lifespan_context
    memories = app.memory.recall(subject, k=50)
    return json.dumps([m.__dict__ for m in memories])
```

---

## Data Flow Sequences

### Session Start Flow

```
┌─────────┐     ┌───────────┐     ┌────────────┐     ┌─────────┐
│ Claude  │     │   Hook    │     │ MemoryStore│     │  Speak  │
│  Code   │     │  Command  │     │            │     │         │
└────┬────┘     └─────┬─────┘     └──────┬─────┘     └────┬────┘
     │                │                  │                │
     │ SessionStart   │                  │                │
     │───────────────>│                  │                │
     │                │                  │                │
     │                │ recall(context)  │                │
     │                │─────────────────>│                │
     │                │                  │                │
     │                │    memories[]    │                │
     │                │<─────────────────│                │
     │                │                  │                │
     │                │         say(greeting)             │
     │                │─────────────────────────────────->│
     │                │                  │                │
     │                │                  │           [audio]
     │                │                  │                │
     │   {status, recent_context}        │                │
     │<───────────────│                  │                │
     │                │                  │                │
```

### Memory Recall Flow (MCP)

```
┌─────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐
│ Claude  │     │    MCP    │     │ MemoryStore│     │  Ollama  │
│  Agent  │     │   Server  │     │            │     │ (embed)  │
└────┬────┘     └─────┬─────┘     └──────┬─────┘     └────┬─────┘
     │                │                  │                │
     │ recall(query)  │                  │                │
     │───────────────>│                  │                │
     │                │                  │                │
     │                │ recall(query, k) │                │
     │                │─────────────────>│                │
     │                │                  │                │
     │                │                  │ embed(query)   │
     │                │                  │───────────────>│
     │                │                  │                │
     │                │                  │   vector[]     │
     │                │                  │<───────────────│
     │                │                  │                │
     │                │                  │ [vec search]   │
     │                │                  │ [fts search]   │
     │                │                  │ [merge+rank]   │
     │                │                  │                │
     │                │    Memory[]      │                │
     │                │<─────────────────│                │
     │                │                  │                │
     │   [{subject, content, relevance}] │                │
     │<───────────────│                  │                │
     │                │                  │                │
```

### Remember Flow (MCP)

```
┌─────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐
│ Claude  │     │    MCP    │     │ MemoryStore│     │  Ollama  │
│  Agent  │     │   Server  │     │            │     │ (embed)  │
└────┬────┘     └─────┬─────┘     └──────┬─────┘     └────┬─────┘
     │                │                  │                │
     │ remember(s, c) │                  │                │
     │───────────────>│                  │                │
     │                │                  │                │
     │                │ remember(s, c)   │                │
     │                │─────────────────>│                │
     │                │                  │                │
     │                │                  │ embed(s + c)   │
     │                │                  │───────────────>│
     │                │                  │                │
     │                │                  │   vector[]     │
     │                │                  │<───────────────│
     │                │                  │                │
     │                │                  │ [INSERT memories]
     │                │                  │ [INSERT memories_vec]
     │                │                  │                │
     │                │    memory_id     │                │
     │                │<─────────────────│                │
     │                │                  │                │
     │   "Remembered: ..."               │                │
     │<───────────────│                  │                │
     │                │                  │                │
```

---

## Hook Input/Output Protocol

### stdin (JSON from Claude Code)

```json
{
  "hook": "Stop",
  "stop_reason": "end_turn",
  "session_id": "abc123",
  "tool_name": null,
  "tool_input": null
}
```

### stdout (JSON to Claude Code)

```json
{
  "status": "success",
  "message": "Optional message for Claude to see",
  "inject": "Optional text to inject into conversation"
}
```

### Hook Behaviors

| Hook | Receives | Can Output | Can Block |
|------|----------|------------|-----------|
| `SessionStart` | session_id, cwd | status, context | No |
| `SessionEnd` | session_id, duration | status | No |
| `Stop` | stop_reason | inject content | No |
| `Notification` | message, title | - | No |
| `PreToolUse` | tool_name, tool_input | - | Yes (exit 1) |
| `PostToolUse` | tool_name, tool_result | - | No |

---

## File Locations

```
~/.config/personality/
├── carts/
│   └── bt7274.yml           # Personality definition
├── voices/
│   └── bt7274.onnx          # Piper voice model
└── memory/
    └── bt7274.db            # sqlite-vec database

~/.claude/
├── settings.json            # Hooks + MCP config
└── commands/psn/            # Slash commands
    ├── speak.md
    ├── cart.md
    ├── carts.md
    ├── voices.md
    ├── status.md
    ├── remember.md          # NEW
    └── recall.md            # NEW
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PERSONALITY_CART` | `bt7274` | Active cart name |
| `PERSONALITY_VOICE_DIR` | `~/.config/personality/voices` | Voice model directory |
| `PERSONALITY_MEMORY_DIR` | `~/.config/personality/memory` | Memory database directory |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `nomic-embed-text` | Embedding model |

---

## New Slash Commands

### /psn:remember

```markdown
# Remember

Store information in long-term memory.

Use the `mcp__personality__remember` tool with:
- `subject`: Category path (e.g., "user.preference.editor", "project.tech.stack")
- `content`: The information to store

Subject prefixes:
- `user.*` - User information
- `self.*` - AI's own attributes
- `project.*` - Current project details
- `general.*` - Shared knowledge
```

### /psn:recall

```markdown
# Recall

Search long-term memory for relevant information.

Use the `mcp__personality__recall` tool with:
- `query`: Natural language search query
- `limit`: Maximum results (default: 5)

Results include relevance scores (0.0-1.0).
```

---

## Complete Tool List (Updated)

### Personality MCP Tools

| Tool | Parameters | Purpose |
|------|------------|---------|
| `mcp__personality__speak` | `text`, `voice?` | Speak text aloud |
| `mcp__personality__remember` | `subject`, `content` | Store memory |
| `mcp__personality__recall` | `query`, `limit?` | Search memories |
| `mcp__personality__forget` | `memory_id` | Delete memory |
| `mcp__personality__consolidate` | `threshold?` | Merge duplicates |

### Personality MCP Resources

| URI | Purpose |
|-----|---------|
| `personality://cart` | Current cart data |
| `personality://cart/{name}` | Specific cart |
| `personality://memories` | All memories |
| `personality://memories/{subject}` | Memories by subject |

---

_Compiled: 2026-02-11_
_No external shell scripts. Direct exec only._
