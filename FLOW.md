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

## TTS Protocol

### Golden Rule

**Speak status, not content.** TTS is for awareness, not information transfer.

### Message Categories

| Category | Speak? | Max Length | Examples |
|----------|--------|------------|----------|
| **Greeting** | Yes | 2 sentences | "Neural link established." |
| **Confirmation** | Yes | 1 sentence | "Objective complete." |
| **Warning** | Yes | 1 sentence | "Warning. Security vulnerability detected." |
| **Status** | Yes | 1 sentence | "Standing by, Pilot." |
| **Notification** | Yes | 1 sentence | "Task complete." |
| **Analysis** | No | - | Technical breakdowns, code reviews |
| **Lists** | No | - | File lists, search results, options |
| **Code** | No | - | Any code blocks or snippets |
| **Explanations** | No | - | Multi-paragraph descriptions |
| **Tables** | No | - | Data tables, comparisons |

### What to Speak

**Progress/Starting (brief):**
```
✓ "Analyzing."
✓ "Stand by, Pilot."
✓ "Searching."
✓ "Compiling."
✓ "Initiating scan."
```

**Completion/Summary (fuller, 1-2 sentences):**
```
✓ "Objective complete, Pilot. Three vulnerabilities identified and patched."
✓ "Migration plan drafted. Ready for implementation on your command."
✓ "Analysis complete. I have identified the root cause in the authentication module."
✓ "Neural link established. All systems operational."
✓ "TTS protocol documented, Pilot. Stop functionality added to MCP tools and CLI."
```

**Warnings (clear and specific):**
```
✓ "Warning. I have detected a security vulnerability in the API endpoint."
✓ "Caution, Pilot. This operation will delete 47 files."
```

### What NOT to Speak

```
✗ "The function on line 47 has a bug because the variable..."
✗ "Here are the 15 files matching your pattern..."
✗ "Let me explain how this authentication system works..."
✗ "The options are: 1) Redis 2) PostgreSQL 3) SQLite..."
✗ Code blocks of any kind
✗ Tables or structured data
```

### TTS Length Limits

| Context | Words | Guidance |
|---------|-------|----------|
| **Progress/Starting** | 2-5 | Brief, single phrase |
| **Completion/Summary** | 10-20 | 1-2 full sentences, convey what was accomplished |
| **Greeting** | 8-15 | Establish presence, can include tagline |
| **Warning** | 10-18 | Clear, specific, include the threat |
| **Farewell** | 5-10 | Brief acknowledgment |

### Tone Calibration

**Too short (robotic, uninformative):**
```
✗ "Done."
✗ "Complete."
✗ "Yes."
```

**Just right (informative, natural):**
```
✓ "Objective complete, Pilot."
✓ "Analysis complete. The issue is in the config parser."
✓ "Standing by for further instructions."
```

**Too long (reading content, not summarizing):**
```
✗ "I have completed the analysis and found that the function on line 47..."
✗ "The migration plan includes five phases: first we will..."
```

### Stop TTS

The Pilot can interrupt TTS at any time:

**MCP Tool:**
```python
@mcp.tool()
def stop_speaking(ctx: Context = None) -> str:
    """
    Immediately stop any ongoing TTS playback.
    Use when the Pilot needs to interrupt or has heard enough.
    """
    app = ctx.request_context.lifespan_context
    app.speak.stop()
    return "TTS stopped"
```

**CLI Command:**
```bash
psn stop       # Stop current playback
psn silence    # Alias
```

**Keyboard Shortcut (if configured):**
```
Ctrl+Shift+S  → uv run psn stop
```

### Implementation

```python
# src/personality/speak.py

class Speak:
    def __init__(self, voice_dir: Path):
        self._cache: dict[str, PiperVoice] = {}
        self._process: subprocess.Popen | None = None  # Track playback process

    def say(self, text: str, voice: str) -> None:
        """Speak text, replacing any current playback."""
        self.stop()  # Stop any existing playback
        wav_data = self._synthesize(text, voice)
        self._play(wav_data)

    def stop(self) -> None:
        """Stop current TTS playback."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    def _play(self, wav_data: bytes) -> None:
        """Play audio, storing process handle for interruption."""
        for player, args in self._players():
            try:
                self._process = subprocess.Popen(
                    [player, *args],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._process.communicate(input=wav_data)
                return
            except FileNotFoundError:
                continue

    def _players(self) -> list[tuple[str, list[str]]]:
        return [
            ("ffplay", ["-nodisp", "-autoexit", "-"]),
            ("afplay", ["-"]),  # macOS
            ("aplay", ["-"]),   # Linux
        ]
```

### PID File for External Stop

```python
# Write PID when starting playback
PID_FILE = Path("~/.config/personality/.tts_pid").expanduser()

def _play(self, wav_data: bytes) -> None:
    # ... start process ...
    PID_FILE.write_text(str(self._process.pid))

def stop(self) -> None:
    # Try stored PID first (for external stop command)
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, ValueError):
            pass
        PID_FILE.unlink(missing_ok=True)
    # Then try internal process handle
    # ...
```

### CLI Stop Command

```python
# src/personality/cli.py

@cli.command()
def stop():
    """Stop current TTS playback."""
    pid_file = Path("~/.config/personality/.tts_pid").expanduser()
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text())
            os.kill(pid, signal.SIGTERM)
            click.echo("TTS stopped")
        except ProcessLookupError:
            click.echo("No active playback")
        finally:
            pid_file.unlink(missing_ok=True)
    else:
        click.echo("No active playback")


@cli.command()
def silence():
    """Alias for stop."""
    ctx = click.get_current_context()
    ctx.invoke(stop)
```

### Agent Guidelines

When using `mcp__personality__speak`, follow these protocols:

1. **One call per response** - Speak once at the start OR end, not both
2. **Match length to context:**
   - Starting work → brief ("Analyzing the codebase.")
   - Finished work → fuller ("Migration complete, Pilot. Database schema updated and tests passing.")
3. **Summarize, do not read** - Convey the outcome, not the details
4. **No code** - Never speak variable names, function signatures, or syntax
5. **No lists** - Say "Found 5 matches in the auth module" not the matches themselves
6. **Be natural** - Avoid robotic one-word responses; a full sentence sounds better

### Hook-Specific TTS

| Hook | TTS Behavior |
|------|--------------|
| `SessionStart` | Greeting (cart tagline) |
| `SessionEnd` | Farewell ("Session complete") |
| `Stop` | Brief status only if `end_turn` |
| `Notification` | Notification title only |
| `PreToolUse` | Silent |
| `PostToolUse` | Silent |

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

    Length guidance:
    - Progress/starting: brief (2-5 words) - "Analyzing." / "Stand by, Pilot."
    - Completion/summary: fuller (10-20 words) - "Objective complete. Three issues resolved."
    - Warnings: clear and specific (10-18 words)

    Do NOT speak: code, lists, multi-paragraph explanations, raw data.

    Args:
        text: Text to speak (1-2 sentences, natural phrasing)
        voice: Optional voice override (defaults to cart voice)
    """
    app = ctx.request_context.lifespan_context
    voice = voice or app.cart.voice
    app.speak.say(text, voice)
    return f"Spoke: {text[:50]}..."


@mcp.tool()
def stop_speaking(ctx: Context = None) -> str:
    """
    Immediately stop any ongoing TTS playback.
    Use when the Pilot needs to interrupt or has heard enough.
    """
    app = ctx.request_context.lifespan_context
    app.speak.stop()
    return "TTS stopped"


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
| `mcp__personality__speak` | `text`, `voice?` | Speak text aloud (short messages only) |
| `mcp__personality__stop_speaking` | - | Stop current TTS playback |
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
