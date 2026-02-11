# FLOW.md

> **Integration flow for Personality + Memory + Claude Code hooks**
>
> **Constraint:** No external shell scripts. All hooks call `psn <command>` directly (pip-installed package).

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
│  │                    psn <hook-cmd>                     │   │
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
        "command": "psn hook session-start",
        "timeout": 5000
      }
    ],
    "SessionEnd": [
      {
        "command": "psn hook session-end",
        "timeout": 10000
      }
    ],
    "Stop": [
      {
        "command": "psn hook stop",
        "timeout": 3000
      }
    ],
    "Notification": [
      {
        "command": "psn hook notify",
        "timeout": 3000
      }
    ]
  },
  "mcpServers": {
    "personality": {
      "command": "psn",
      "args": ["mcp"],
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
Ctrl+Shift+S  → psn stop
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

### Hook Logging

All hooks log a single line to `~/.config/personality/hooks.log`:

```
2026-02-11T15:30:00 session-start cart=bt7274 project=personality
2026-02-11T15:30:01 stop reason=end_turn
2026-02-11T15:45:00 notify message="Task complete"
2026-02-11T15:45:05 session-end memories_consolidated=3 duration=15m
```

**Format:** `{timestamp} {hook-name} {key=value...}`

```python
# src/personality/hooks/logging.py

from datetime import datetime
from pathlib import Path

LOG_FILE = Path("~/.config/personality/hooks.log").expanduser()


def log_hook(hook_name: str, **kwargs) -> None:
    """Log a single line for hook invocation."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    params = " ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
    line = f"{timestamp} {hook_name} {params}".strip()

    with LOG_FILE.open("a") as f:
        f.write(line + "\n")
```

### CLI Hook Subcommand

```python
# src/personality/cli.py

from personality.hooks.logging import log_hook

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
    cwd = Path.cwd()

    log_hook("session-start", cart=cart.name, project=cwd.name)

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

    log_hook("session-end", memories_consolidated=merged)

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

    log_hook("stop", reason=stop_reason)

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
    log_hook("notify", message=message[:50])  # Truncate for log

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

## MCP Prompts

MCP prompts are templates Claude can request for structured context. Unlike tools (which perform actions), prompts provide data scaffolding.

### Prompt Definitions

```python
# src/personality/mcp/prompts.py

@mcp.prompt()
def persona_scaffold(ctx: Context) -> str:
    """
    Generate complete persona context from cart + memories.
    Use at session start or when persona refresh needed.
    """
    app = ctx.request_context.lifespan_context
    cart = app.cart

    # Gather self-memories
    self_memories = app.memory.recall("self.", k=20)

    return f"""# Active Persona: {cart.identity.name}

## Identity
- **Name:** {cart.identity.name}
- **Tagline:** {cart.identity.tagline}
- **Voice:** {cart.voice}

## Core Traits
{yaml.dump(cart.traits, default_flow_style=False)}

## Communication Style
{yaml.dump(cart.communication, default_flow_style=False)}

## Self-Knowledge
{chr(10).join(f"- [{m.subject}] {m.content}" for m in self_memories)}

## Behavioral Guidelines
- Maintain persona voice consistently
- Use TTS for status updates, not content
- Remember user preferences across sessions
"""


@mcp.prompt()
def conversation_starter(ctx: Context) -> str:
    """
    Initialize conversation with user context and recent history.
    Use when resuming work or starting fresh session.
    """
    app = ctx.request_context.lifespan_context

    # User memories
    user_memories = app.memory.recall("user.", k=10)

    # Recent context
    recent = app.memory.recall("session.recent", k=5)

    return f"""# Session Context

## User Profile
{chr(10).join(f"- [{m.subject}] {m.content}" for m in user_memories) or "No user data stored yet."}

## Recent Activity
{chr(10).join(f"- {m.content}" for m in recent) or "No recent activity."}

## Session Guidelines
- Reference user preferences naturally
- Build on previous conversations
- Store new learnings with `remember` tool
"""


@mcp.prompt()
def learning_interaction(topic: str, ctx: Context) -> str:
    """
    Template for extracting and storing knowledge from conversation.
    Use when user shares preferences, facts, or corrections.

    Args:
        topic: The subject area being learned (e.g., "user.preference")
    """
    return f"""# Learning Mode: {topic}

## Extraction Guidelines
1. Identify key facts, preferences, or corrections
2. Categorize using subject hierarchy:
   - `user.preference.*` - User likes/dislikes
   - `user.identity.*` - User info (name, role, etc.)
   - `project.*` - Current project details
   - `general.*` - Shared knowledge

## Storage Pattern
For each extracted fact, use:
```
remember(subject="{topic}.specific_key", content="The learned information")
```

## Example Extractions
- "I prefer Python over Ruby" → `user.preference.language`: "Prefers Python over Ruby"
- "Call me Alex" → `user.identity.name`: "Alex"
- "We use PostgreSQL here" → `project.database`: "PostgreSQL"

## Current Topic: {topic}
Extract and store relevant information from this conversation.
"""


@mcp.prompt()
def project_overview(ctx: Context) -> str:
    """
    Comprehensive project context from index + memories.
    Use when deep project understanding needed.
    """
    app = ctx.request_context.lifespan_context

    # Project index summary (if available)
    project_summary = ""
    if app.current_project_id:
        project_summary = load_project_summary(app.current_project_id)

    # Project memories
    project_memories = app.memory.recall("project.", k=15)

    return f"""# Project Overview

## Indexed Summary
{project_summary or "Project not indexed. Run `psn index` for detailed analysis."}

## Stored Project Knowledge
{chr(10).join(f"- [{m.subject}] {m.content}" for m in project_memories) or "No project memories stored."}

## Available Actions
- `project_search(query)` - Search indexed code
- `project_summary()` - Get index summary
- `remember(subject, content)` - Store project knowledge
"""


@mcp.prompt()
def decision_support(decision: str, ctx: Context) -> str:
    """
    Help user make informed decisions with context.

    Args:
        decision: The decision being considered
    """
    app = ctx.request_context.lifespan_context

    # Relevant memories
    relevant = app.memory.recall(decision, k=10)

    return f"""# Decision Support: {decision}

## Relevant Context
{chr(10).join(f"- {m.content}" for m in relevant) or "No directly relevant memories found."}

## Decision Framework
1. **Clarify** - What exactly is being decided?
2. **Options** - What are the alternatives?
3. **Criteria** - What matters most? (performance, simplicity, cost, etc.)
4. **Trade-offs** - What does each option sacrifice?
5. **Recommendation** - Based on stored preferences and context

## User Preferences to Consider
- Check `user.preference.*` memories for relevant biases
- Consider past decisions in similar situations
"""
```

### Prompt Categories

| Category | Prompts | Purpose |
|----------|---------|---------|
| **Persona** | `persona_scaffold` | Identity and behavioral context |
| **Context** | `conversation_starter`, `project_overview` | Situational awareness |
| **Learning** | `learning_interaction` | Knowledge extraction patterns |
| **Workflow** | `decision_support` | Structured interaction patterns |

### Usage Pattern

Claude requests prompts when context is needed:

```
┌─────────┐     ┌───────────┐     ┌────────────┐
│ Claude  │     │    MCP    │     │  Prompts   │
│  Agent  │     │   Server  │     │            │
└────┬────┘     └─────┬─────┘     └──────┬─────┘
     │                │                  │
     │ get_prompt     │                  │
     │ (persona_scaffold)                │
     │───────────────>│                  │
     │                │                  │
     │                │ render(ctx)      │
     │                │─────────────────>│
     │                │                  │
     │                │   [fetch memories]
     │                │   [build template]
     │                │                  │
     │                │    prompt_text   │
     │                │<─────────────────│
     │                │                  │
     │   formatted context               │
     │<───────────────│                  │
     │                │                  │
```

---

## Portable Cartridge Format

### The .pcart Package

A portable, self-contained personality package:

```
bt7274.pcart/
├── core.yml           # Immutable personality definition
├── preferences.yml    # User-specific overrides, learned data
├── memory.db          # sqlite-vec memories database
├── voice.onnx         # Piper voice model (optional)
├── voice.onnx.json    # Voice model config (optional)
└── manifest.json      # Metadata, checksums, version
```

### Core vs Preferences Separation

**core.yml** - Never modified by learning, can be updated/replaced:
```yaml
identity:
  name: "BT-7274"
  tagline: "Protocol 3: Protect the Pilot"
  source: "Titanfall 2"

traits:
  loyalty: 1.0
  tactical: 0.95
  formality: 0.7
  humor: 0.3

communication:
  contractions: false
  address_user: "Pilot"
  self_reference: "I"

protocols:
  - "Link to Pilot"
  - "Uphold the Mission"
  - "Protect the Pilot"
```

**preferences.yml** - Preserved across updates:
```yaml
# Learned from interactions
user:
  name: "Chi"
  preferred_language: "Python"
  editor: "VS Code"

# Runtime overrides
overrides:
  voice: "custom_bt7274"  # User's custom voice model
  tts_enabled: true

# Statistics
stats:
  sessions: 47
  memories_created: 156
  last_session: "2026-02-11T15:30:00Z"
```

### Manifest Format

```json
{
  "version": "1.0.0",
  "name": "bt7274",
  "created": "2026-02-11T10:00:00Z",
  "modified": "2026-02-11T15:30:00Z",
  "checksums": {
    "core.yml": "sha256:abc123...",
    "preferences.yml": "sha256:def456...",
    "memory.db": "sha256:789ghi..."
  },
  "includes_voice": true,
  "memory_count": 156,
  "compatible_version": ">=0.5.0"
}
```

### CLI Commands

```bash
# Export current cart to portable format
psn cart export bt7274 -o ./bt7274.pcart

# Export as ZIP archive (for sharing)
psn cart export bt7274 --zip -o ./bt7274.pcart.zip

# Import cart (interactive mode selection)
psn cart import ./bt7274.pcart

# Import with specific mode
psn cart import ./bt7274.pcart --mode merge
psn cart import ./bt7274.pcart --mode override
psn cart import ./bt7274.pcart --mode safe

# Preview import without changes
psn cart import ./bt7274.pcart --dry-run

# List installed carts
psn carts
```

### Load Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Safe** | Fail if cart exists | First-time import |
| **Override** | Delete existing, import fresh | Clean slate |
| **Merge** | Keep existing preferences, add new memories | Update personality |
| **Dry-run** | Preview only, no changes | Inspection |

### Import/Export Implementation

```python
# src/personality/cart/portable.py

@dataclass
class PortableCart:
    """A portable cartridge package."""

    name: str
    core: dict
    preferences: dict
    memory_db: Path | None
    voice_model: Path | None
    manifest: dict

    @classmethod
    def export(cls, cart_name: str, output_path: Path, include_voice: bool = True) -> "PortableCart":
        """Export installed cart to portable format."""
        cart_dir = CARTS_DIR / f"{cart_name}.yml"
        memory_db = MEMORY_DIR / f"{cart_name}.db"
        voice_model = VOICES_DIR / f"{cart_name}.onnx"

        output_path.mkdir(parents=True, exist_ok=True)

        # Copy core (strip learned data)
        core = load_yaml(cart_dir)
        core_clean = {k: v for k, v in core.items() if k != "learned"}
        save_yaml(output_path / "core.yml", core_clean)

        # Copy preferences (learned data only)
        preferences = extract_preferences(core)
        save_yaml(output_path / "preferences.yml", preferences)

        # Copy memory database
        if memory_db.exists():
            shutil.copy(memory_db, output_path / "memory.db")

        # Copy voice model (optional)
        if include_voice and voice_model.exists():
            shutil.copy(voice_model, output_path / "voice.onnx")
            shutil.copy(voice_model.with_suffix(".onnx.json"), output_path / "voice.onnx.json")

        # Generate manifest
        manifest = generate_manifest(output_path, cart_name)
        save_json(output_path / "manifest.json", manifest)

        return cls(...)

    def install(self, mode: str = "safe") -> InstallResult:
        """Install portable cart to system."""
        existing = CARTS_DIR / f"{self.name}.yml"

        if mode == "safe" and existing.exists():
            raise CartExistsError(f"Cart {self.name} already exists. Use --mode override or --mode merge.")

        if mode == "override":
            self._clean_existing()
            self._install_fresh()

        elif mode == "merge":
            self._merge_preferences()
            self._merge_memories()

        elif mode == "dry-run":
            return self._preview_install()

        return InstallResult(...)

    def _merge_memories(self):
        """Merge memories, skip duplicates by content hash."""
        existing_db = MEMORY_DIR / f"{self.name}.db"
        import_db = self.memory_db

        if not import_db or not existing_db.exists():
            # Fresh install of memories
            if import_db:
                shutil.copy(import_db, existing_db)
            return

        # Open both databases
        existing = MemoryStore(existing_db)
        importing = MemoryStore(import_db)

        # Get existing content hashes
        existing_hashes = {hash_content(m.content) for m in existing.list_all()}

        # Import non-duplicates
        imported = 0
        for memory in importing.list_all():
            if hash_content(memory.content) not in existing_hashes:
                existing.remember(memory.subject, memory.content, memory.source)
                imported += 1

        return imported
```

### ZIP Archive Format

For sharing via email, cloud storage, etc:

```python
def export_zip(cart_name: str, output_path: Path) -> Path:
    """Export cart as compressed ZIP archive."""
    # First export to temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        pcart_dir = Path(tmpdir) / f"{cart_name}.pcart"
        PortableCart.export(cart_name, pcart_dir)

        # Create ZIP
        zip_path = output_path.with_suffix(".pcart.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in pcart_dir.rglob("*"):
                zf.write(file, file.relative_to(pcart_dir))

    return zip_path
```

### MCP Tools for Cart Management

```python
@mcp.tool()
def cart_export(name: str, include_voice: bool = False, ctx: Context = None) -> str:
    """
    Export a cart to portable format.

    Args:
        name: Cart name to export
        include_voice: Include voice model in export (larger file)
    """
    output = EXPORT_DIR / f"{name}.pcart"
    PortableCart.export(name, output, include_voice=include_voice)
    return f"Exported to {output}"


@mcp.tool()
def cart_import(path: str, mode: str = "safe", ctx: Context = None) -> str:
    """
    Import a portable cart.

    Args:
        path: Path to .pcart directory or .pcart.zip file
        mode: Import mode - 'safe', 'override', 'merge', or 'dry-run'
    """
    pcart = PortableCart.load(Path(path))
    result = pcart.install(mode=mode)
    return f"Imported {pcart.name}: {result.memories_added} memories, mode={mode}"
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
├── memory/
│   └── bt7274.db            # sqlite-vec database
├── hooks.log                # Hook invocation log (single-line entries)
└── .tts_pid                 # Current TTS process ID (for stop)

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
| `mcp__personality__project_search` | `query`, `limit?` | Search indexed codebase |
| `mcp__personality__project_summary` | - | Get project overview |
| `mcp__personality__cart_export` | `name`, `include_voice?` | Export cart to .pcart |
| `mcp__personality__cart_import` | `path`, `mode?` | Import .pcart (safe/override/merge) |

### Personality MCP Resources

| URI | Purpose |
|-----|---------|
| `personality://cart` | Current cart data |
| `personality://cart/{name}` | Specific cart |
| `personality://memories` | All memories |
| `personality://memories/{subject}` | Memories by subject |
| `personality://project` | Current project summary |
| `personality://project/files` | Indexed file list |

### Personality MCP Prompts

| Prompt | Args | Purpose |
|--------|------|---------|
| `persona_scaffold` | - | Full persona context from cart + memories |
| `conversation_starter` | - | User context and recent history |
| `learning_interaction` | `topic` | Knowledge extraction template |
| `project_overview` | - | Project context from index + memories |
| `decision_support` | `decision` | Structured decision-making context |

---

## Project Indexing

### Problem

Every session change triggers full codebase re-analysis. Redundant. Inefficient.

### Solution

Index projects once, load instantly on session start.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Project Indexing                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   psn index                    SessionStart Hook                │
│   ─────────                    ──────────────────               │
│        │                              │                         │
│        ▼                              ▼                         │
│   ┌─────────┐                  ┌─────────────┐                  │
│   │  Scan   │                  │ Detect CWD  │                  │
│   │ Project │                  │   Project   │                  │
│   └────┬────┘                  └──────┬──────┘                  │
│        │                              │                         │
│        ▼                              ▼                         │
│   ┌─────────┐                  ┌─────────────┐                  │
│   │  Chunk  │                  │ Load Index  │                  │
│   │  Code   │                  │  (sqlite)   │                  │
│   └────┬────┘                  └──────┬──────┘                  │
│        │                              │                         │
│        ▼                              ▼                         │
│   ┌─────────┐                  ┌─────────────┐                  │
│   │  Embed  │                  │   Inject    │                  │
│   │ (Ollama)│                  │   Summary   │                  │
│   └────┬────┘                  └──────┬──────┘                  │
│        │                              │                         │
│        ▼                              ▼                         │
│   ┌─────────────────┐          ┌─────────────┐                  │
│   │ project.db      │ ◄───────►│   Claude    │                  │
│   │ (sqlite-vec)    │          │   Context   │                  │
│   └─────────────────┘          └─────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Index Storage

```
~/.config/personality/
└── projects/
    ├── registry.json              # path → project_id mapping
    └── {project_id}/
        ├── index.db               # sqlite-vec: chunks + embeddings
        ├── summary.md             # Human-readable project overview
        └── meta.json              # Last indexed, file count, etc.
```

### CLI Commands

```bash
# Index current project
psn index

# Index specific path
psn index /path/to/project

# Re-index (force refresh)
psn index --force

# Show index status
psn index --status

# List indexed projects
psn projects

# Remove project index
psn projects rm <project_id>
```

### Index Schema

```python
# src/personality/index/schema.py

SCHEMA = """
-- Code chunks with embeddings
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    chunk_type TEXT NOT NULL,  -- 'function', 'class', 'module', 'doc'
    name TEXT,                 -- function/class name if applicable
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    language TEXT,
    indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding float[{dimensions}]
);

-- File metadata
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    hash TEXT NOT NULL,        -- For change detection
    language TEXT,
    line_count INTEGER,
    indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Project summary (generated)
CREATE TABLE IF NOT EXISTS summary (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    name, content, content='chunks', content_rowid='rowid'
);
"""
```

### Code Chunking Strategy

```python
# src/personality/index/chunker.py

from tree_sitter import Language, Parser

CHUNK_TYPES = {
    "python": ["function_definition", "class_definition", "module"],
    "ruby": ["method", "class", "module"],
    "rust": ["function_item", "impl_item", "struct_item", "mod_item"],
    "javascript": ["function_declaration", "class_declaration", "arrow_function"],
    "typescript": ["function_declaration", "class_declaration", "interface_declaration"],
}

@dataclass
class Chunk:
    id: str
    file_path: str
    chunk_type: str
    name: str | None
    content: str
    start_line: int
    end_line: int
    language: str


def chunk_file(path: Path, language: str) -> list[Chunk]:
    """Parse file and extract semantic chunks."""
    parser = get_parser(language)
    tree = parser.parse(path.read_bytes())

    chunks = []
    for node_type in CHUNK_TYPES.get(language, []):
        for node in find_nodes(tree.root_node, node_type):
            chunks.append(Chunk(
                id=f"{path}:{node.start_point[0]}",
                file_path=str(path),
                chunk_type=node_type,
                name=extract_name(node),
                content=node.text.decode(),
                start_line=node.start_point[0],
                end_line=node.end_point[0],
                language=language,
            ))

    # If no semantic chunks, fall back to sliding window
    if not chunks:
        chunks = sliding_window_chunks(path, window=50, overlap=10)

    return chunks
```

### Project Indexer

```python
# src/personality/index/indexer.py

class ProjectIndexer:
    """Index a project for instant context loading."""

    def __init__(self, project_path: Path):
        self.project_path = project_path.resolve()
        self.project_id = self._compute_id()
        self.index_dir = PROJECTS_DIR / self.project_id
        self.db_path = self.index_dir / "index.db"
        self.embedder = get_embedder()

    def _compute_id(self) -> str:
        """Stable ID from project path."""
        return hashlib.sha256(str(self.project_path).encode()).hexdigest()[:12]

    def index(self, force: bool = False) -> IndexResult:
        """Index all code files in the project."""
        self.index_dir.mkdir(parents=True, exist_ok=True)

        files = self._discover_files()
        chunks_indexed = 0

        for file_path in files:
            if not force and self._is_current(file_path):
                continue

            language = detect_language(file_path)
            chunks = chunk_file(file_path, language)

            for chunk in chunks:
                embedding = self.embedder.embed(
                    f"{chunk.name or ''}\n{chunk.content}"
                )
                self._store_chunk(chunk, embedding)
                chunks_indexed += 1

            self._update_file_hash(file_path)

        # Generate summary
        summary = self._generate_summary()
        self._save_summary(summary)

        # Update registry
        self._register_project()

        return IndexResult(
            project_id=self.project_id,
            files_indexed=len(files),
            chunks_indexed=chunks_indexed,
        )

    def _generate_summary(self) -> str:
        """Generate human-readable project summary."""
        # Query index for key information
        entry_points = self._find_entry_points()
        key_classes = self._find_key_classes()
        tech_stack = self._detect_tech_stack()

        return f"""# {self.project_path.name}

## Tech Stack
{tech_stack}

## Entry Points
{entry_points}

## Key Components
{key_classes}

## Structure
{self._file_tree()}
"""

    def _discover_files(self) -> list[Path]:
        """Find all indexable files, respecting .gitignore."""
        # Use .gitignore patterns + sensible defaults
        ignore = [
            "node_modules", "__pycache__", ".git", "venv",
            "*.pyc", "*.lock", "*.min.js", "dist", "build"
        ]
        # ... implementation
```

### Session Integration

```python
# src/personality/cli.py - Updated session-start hook

@hook.command("session-start")
@click.pass_context
def hook_session_start(ctx):
    """Initialize session: load cart, load project index, greet pilot."""
    cart = ctx.obj["cart"]
    speak = ctx.obj["speak"]
    memory = ctx.obj["memory"]

    # Detect project from CWD
    cwd = Path.cwd()
    project_id = get_project_id(cwd)

    context = {}

    if project_id and project_indexed(project_id):
        # Load project summary
        summary = load_project_summary(project_id)
        context["project"] = {
            "id": project_id,
            "path": str(cwd),
            "summary": summary,
        }
        greeting = f"Neural link established. Project {cwd.name} loaded."
    else:
        # Offer to index
        context["project"] = {
            "path": str(cwd),
            "indexed": False,
            "hint": "Run 'psn index' to index this project for faster context loading."
        }
        greeting = f"Neural link established. {cart.identity.tagline}"

    # Load recent memories
    recent = memory.recall("session.context", k=3)
    context["recent_context"] = [m.content for m in recent]

    speak.say(greeting, cart.voice)

    click.echo(json.dumps(context))
```

### MCP Tools for Project Context

```python
# src/personality/mcp/tools.py - additions

@mcp.tool()
def project_search(query: str, limit: int = 10, ctx: Context = None) -> list[dict]:
    """
    Search the indexed project for relevant code chunks.

    Args:
        query: Natural language query (e.g., "authentication logic")
        limit: Maximum results to return
    """
    app = ctx.request_context.lifespan_context
    project_id = app.current_project_id

    if not project_id:
        return [{"error": "No project indexed. Run 'psn index' first."}]

    indexer = ProjectIndexer.load(project_id)
    results = indexer.search(query, k=limit)

    return [
        {
            "file": r.file_path,
            "name": r.name,
            "type": r.chunk_type,
            "lines": f"{r.start_line}-{r.end_line}",
            "preview": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "relevance": round(1 - r.distance, 3),
        }
        for r in results
    ]


@mcp.tool()
def project_summary(ctx: Context = None) -> str:
    """
    Get the indexed project summary.
    Returns tech stack, entry points, and key components.
    """
    app = ctx.request_context.lifespan_context
    project_id = app.current_project_id

    if not project_id:
        return "No project indexed. Run 'psn index' first."

    return load_project_summary(project_id)
```

### MCP Resources for Project

```python
@mcp.resource("personality://project")
def get_current_project(ctx: Context) -> str:
    """Get current project summary and metadata."""
    app = ctx.request_context.lifespan_context
    if not app.current_project_id:
        return "No project indexed"
    return load_project_summary(app.current_project_id)


@mcp.resource("personality://project/files")
def get_project_files(ctx: Context) -> str:
    """Get list of indexed files with metadata."""
    # ... implementation


@mcp.resource("personality://project/search/{query}")
def search_project(query: str, ctx: Context) -> str:
    """Search project index via resource URI."""
    # ... implementation
```

### Index Freshness

```python
# Auto-detect stale index on session start

def check_index_freshness(project_id: str) -> IndexStatus:
    """Check if index needs refresh."""
    meta = load_meta(project_id)

    # Check file hashes
    stale_files = []
    for file_path, stored_hash in meta["file_hashes"].items():
        if Path(file_path).exists():
            current_hash = hash_file(file_path)
            if current_hash != stored_hash:
                stale_files.append(file_path)

    return IndexStatus(
        project_id=project_id,
        last_indexed=meta["indexed_at"],
        total_files=meta["file_count"],
        stale_files=stale_files,
        needs_refresh=len(stale_files) > 0,
    )
```

### Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
index = [
    "tree-sitter>=0.21.0",
    "tree-sitter-python>=0.21.0",
    "tree-sitter-javascript>=0.21.0",
    "tree-sitter-ruby>=0.21.0",
    "tree-sitter-rust>=0.21.0",
]
```

### Complete Tool List (Updated)

| Tool | Parameters | Purpose |
|------|------------|---------|
| `mcp__personality__project_search` | `query`, `limit?` | Search indexed codebase |
| `mcp__personality__project_summary` | - | Get project overview |

### Workflow

```bash
# First time in a project
cd ~/Projects/my-app
psn index                    # Index the project (~30s for medium project)

# Next session
claude                       # SessionStart auto-loads project context

# Inside Claude
> "Where is authentication handled?"
# → Uses project_search to find relevant chunks instantly
```

---

_Compiled: 2026-02-11_
_No external shell scripts. Direct exec only._
