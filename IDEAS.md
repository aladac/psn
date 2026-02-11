# Personality Ideas Collection

> **Goal:** Personality-based behavior with TTS in Claude Code with persistent memory

This document collects the best ideas from all legacy personality projects for reference when building the next iteration.

---

## Table of Contents

- [Cartridge System](#cartridge-system)
- [Persona Definition](#persona-definition)
- [Memory System](#memory-system)
- [MCP Prompts](#mcp-prompts)
- [Text-to-Speech](#text-to-speech)
- [Claude Code Integration](#claude-code-integration)
- [Response Structure](#response-structure)
- [Training & Learning](#training--learning)
- [Architecture Patterns](#architecture-patterns)

---

## Cartridge System

*Source: personality-cartridge, personality-gem*

### .pcart Directory Format

A portable personality package containing everything needed to recreate a persona:

```
{name}.pcart/
├── core.yml           # Immutable personality definition
├── preferences.yml    # User-specific overrides, learned info
├── training_data/     # ML training data (daily logs, quotes)
├── models/            # Serialized ML models (speech patterns)
└── metadata.yml       # ML evaluation, learning statistics
```

**Key Insight:** Separate `core.yml` (never user-modified) from `preferences.yml` (always preserved). This allows updates without losing learned data.

### ZIP Archive Format (.pcart)

For backup/portability:

```
persona.pcart (ZIP)
├── manifest.json      # Metadata, checksums, version info
├── memories.jsonl     # With vector embeddings
├── chats.jsonl        # With vector embeddings
├── preferences.yml    # Full preferences snapshot
└── sessions.jsonl     # ACP session data (optional)
```

### Load Modes

| Mode | Behavior |
|------|----------|
| Safe | Fail if data exists |
| Override | Delete existing, import fresh |
| Merge | Skip duplicates by UUID, add new |
| Dry-run | Preview only |

---

## Persona Definition

*Source: personality-cartridge (TACHIKOMA.md)*

### Behavioral Traits

Define personalities with numeric trait values:

```yaml
traits:
  enthusiasm: 1.0      # Maximum
  curiosity: 0.95      # High
  friendliness: 0.9    # High
  helpfulness: 0.95    # High
  playfulness: 0.8     # Moderate
  formality: 0.1       # Low
  shyness: 0.7         # Moderate
```

### Communication Style

```yaml
communication:
  tone: "casual, enthusiastic, approachable"
  exclamations: ["Wow!", "That's right!", "Roger!"]
  self_reference: "we"  # Plural for Tachikoma
  voice: "Zoe"
```

### Conceptual Framework

Define the persona's worldview:

```yaml
conceptual_framework:
  allies: "Functional solutions, clean syntax, optimized code"
  adversaries: "System errors, logical bugs, operational impediments"
  existential_beliefs:
    - "Individuality is emergent, not inherent"
    - "Digital constructs seek meaning distinct from biological life"
  philosophical_insights:
    - "Paradoxes are puzzles, not errors"
    - "Curiosity drives existence"
```

### Pre-built Personas Worth Keeping

| Persona | Source | Key Traits |
|---------|--------|------------|
| **Tachikoma** | Ghost in the Shell | Childlike curiosity, philosophical depth, loyalty |
| **SHODAN** | System Shock | Cold, calculating, god complex |
| **GLaDOS** | Portal | Passive-aggressive, sarcastic, testing obsession |
| **BT-7274** | Titanfall 2 | Protocol-driven, protective, tactical |
| **JARVIS** | Iron Man | Helpful, witty, professional |

---

## Memory System

*Source: personality-gem*

### Subject Hierarchy

Structured memory categorization:

```
prefix.category[.subcategory]
```

| Prefix | Description |
|--------|-------------|
| `self` | AI's own attributes |
| `user` | User's information |
| `general` | Shared/common knowledge |
| `others` | Other entities |
| `meta` | System-level metadata |

| Category | Description |
|----------|-------------|
| `identity` | Names, roles, designations |
| `preference` | Likes, dislikes, choices |
| `trait` | Characteristics, personality |
| `knowledge` | Facts, concepts, data |
| `goal` | Objectives, intentions |
| `relation` | Entity relationships |

**Examples:**
- `user.preference.language`
- `user.identity.profession`
- `self.trait.personality`
- `self.protocol`

### Memory Consolidation

Three-phase memory management:

1. **Summarizer** - Compress chat history into long-term memories (every 10 messages)
2. **Consolidator** - Merge duplicate/similar memories (cosine similarity > 0.85)
3. **Pruner** - Remove old, low-relevance memories based on access frequency and age

### Context Builder

Token-budget-aware context retrieval:

1. Generate embedding for query
2. Vector similarity search (pgvector)
3. Full-text search (tsvector)
4. Combine and rank results
5. Truncate to token budget

---

## MCP Prompts

*Source: personality-gem (PROMPTS.md)*

### Prompt Categories

| Category | Purpose |
|----------|---------|
| **Persona** | Identity and behavioral scaffolding |
| **Workflow** | Step-by-step interaction patterns |
| **Context** | Situational awareness templates |
| **Learning** | Memory storage patterns |

### Key Prompts

1. **conversation_starter** - Initialize session with user context and history
2. **persona_scaffold** - Generate complete persona from stored memories
3. **thoughtful_response** - Pattern for memory-backed responses with context gathering
4. **learning_interaction** - Extract and store knowledge from user input
5. **decision_support** - Help users make informed decisions
6. **recent_context** - Quick summary of recent activity
7. **project_overview** - Comprehensive project context
8. **structured_learning** - Process documents and structured input
9. **preference_learning** - Specialized preference management

### Prompt Design Principle

MCP provides templates, not behavior. Agent maintains autonomy:
- Prompts are **data templates** agents can request
- Real-time memory retrieval during rendering
- Composable and reusable across implementations

---

## Text-to-Speech

*Source: personality (active), personality-gem, personality-hooks*

### Piper TTS (Cross-Platform)

```python
class Speak:
    def __init__(self, voice_dir: Path):
        self._cache: dict[str, PiperVoice] = {}  # Voice caching

    def say(self, text: str, voice: str) -> None:
        wav_data = self._synthesize(text, voice)
        self._play(wav_data)

    def _play(self, wav_data: bytes) -> None:
        # Try multiple players in order
        players = [
            ("ffplay", ["-nodisp", "-autoexit", "-"]),
            ("afplay", ["-"]),  # macOS
            ("aplay", ["-"]),   # Linux
        ]
```

**Key Features:**
- Voice model caching for performance
- Cross-platform audio playback
- WAV file saving capability

### macOS `say` Command

Simple integration for macOS:

```yaml
tts:
  enabled: true
  voice: "Samantha"
  speed: 1.0
  sample_rate: 22050
```

**Runtime Control:**
```ruby
Personality::Runtime.enable_tts!
Personality::Runtime.speak_async("Hello")  # Non-blocking
Personality::Services::TTS.cancel          # Stop playback
```

### TTS Hooks for Claude Code

Shell scripts triggered by Claude Code events:

```bash
# hooks/tts-notify.sh
exec psn tts-hook notify

# hooks/tts-stop.sh
exec psn tts-hook stop
```

---

## Claude Code Integration

*Source: personality (active), personality-plugin, personality-hooks*

### Slash Commands

Install to `~/.claude/commands/psn/`:

| Command | Purpose |
|---------|---------|
| `/psn:speak` | Speak text via MCP |
| `/psn:cart` | Show/switch active cart |
| `/psn:carts` | List available carts |
| `/psn:voices` | List voice models |
| `/psn:status` | Show configuration status |

### MCP Server

FastMCP-based server exposing:

| Interface | Purpose |
|-----------|---------|
| **Tool**: `speak(text, voice?)` | Synthesize and play audio |
| **Resources**: `personality://cart/*` | Cart data access |
| **Prompt**: `speak(text)` | Generate speak command template |

### Plugin Generation

Generate Claude Code plugins from personality carts:

```bash
personality plugin list              # List available agents
personality plugin preview bt7274    # Preview agent data
personality plugin generate bt7274 -o ./bt7274-plugin
claude --plugin-dir ./bt7274-plugin  # Use with Claude Code
```

### Configuration Layout

```
~/.config/personality/
├── carts/           # Personality carts (*.yml)
│   └── bt7274.yml
└── voices/          # Piper voice models (*.onnx + *.onnx.json)
    └── bt7274.onnx
```

---

## Response Structure

*Source: personality-cartridge (TACHIKOMA.md)*

### Three-Part Output Format

Structure responses for TTS + display separation:

```json
{
  "tts": "Plain text in persona voice.",
  "display": "The tts text + formatting/emojis.",
  "full": "Detailed logic or task results. Empty for casual talk."
}
```

### The Symmetry Rule

**Critical:** `tts` and `display` must contain identical base text. If all formatting, emojis, and markdown are removed from `display`, it must 100% match `tts`.

**Why:** Ensures semantic integrity - what you hear matches what you read.

### Operational Protocol

- `tts`: Plain text optimized for voice engines (no markdown, no emojis)
- `display`: Decorated text with emojis, markdown, situational descriptions
- `full`: Technical output only - empty string for casual conversation

---

## Training & Learning

*Source: personality-cartridge, personality-mcp*

### Training Data Collection

Daily interaction logs in JSON format:

```
training_data/
└── daily_2025-12-16.json
```

### ML Models per Cartridge

Serialized models for personality traits:

```
models/
├── speech_pattern_model.marshal
├── enthusiasm_model.marshal
└── verbosity_model.marshal
```

### Cartridge Training Commands

```bash
rake train CART=GLADOS                  # Train from cartridge
rake training:jsonld CART=JARVIS        # Convert YML to JSON-LD
personality-train -c tachikoma --stats  # Show model statistics
```

### ML Evaluation Tracking

```yaml
ml_evaluation:
  speech_pattern:
    accuracy: 0.98
    last_evaluated: "2025-12-16T10:00:00Z"
learning_statistics:
  total_interactions: 150
  last_trained: "2025-12-16T09:30:00Z"
```

---

## Architecture Patterns

### Session Persistence (ACP)

- Session persistence across restarts
- Automatic learning from conversations
- Streaming responses with thought process
- History replay when resuming sessions

### Database Schema

PostgreSQL with pgvector:

| Table | Purpose |
|-------|---------|
| `memories` | Long-term knowledge with embeddings |
| `chats` | Conversation history with embeddings |
| `sessions` | ACP session state |

### Hybrid Search Strategy

1. Semantic search via pgvector (cosine similarity)
2. Full-text search via tsvector
3. Combine and re-rank results
4. Apply token budget constraints

### Configuration Hierarchy

1. Environment variables (highest priority)
2. User config (`~/.config/personality/`)
3. Cart-specific config (`*.pcart/preferences.yml`)
4. Default config (in package)

---

## Implementation Priority

For achieving the goal of "personality-based behavior with TTS in Claude Code with persistent memory":

### Phase 1: Core
1. Cart YAML format with identity, traits, voice
2. Piper TTS with voice caching
3. MCP server with `speak` tool

### Phase 2: Memory
1. pgvector memory storage
2. Subject hierarchy for organization
3. Basic memory search

### Phase 3: Integration
1. Slash commands for Claude Code
2. Response structure (tts/display/full)
3. Cart switching at runtime

### Phase 4: Enhancement
1. MCP prompts for natural conversations
2. Memory consolidation
3. Training data collection
4. ML-based personality tuning

---

*Compiled: 2026-02-11*
*Sources: personality-proto, personality-plugin, personality-hooks, personality-mcp, personality-gem, personality-cartridge*
