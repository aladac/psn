# Personality Repository Analysis Report

Generated: 2026-02-16

## Executive Summary

Scanned 9 personality-related repositories across `~/Projects/`. The current `personality` plugin is the **leanest version** - it has good hooks infrastructure but is **missing the entire persona/cartridge system** that was the heart of every previous version.

**Key Finding:** `personality-current` has the most advanced Python implementation and should be the canonical reference for bringing persona features into the current plugin.

---

## Repository Map

| Repo | Tech Stack | Status | Purpose |
|------|-----------|--------|---------|
| `personality` (current) | Python, FastMCP, psn CLI | Active | Claude Code plugin - infrastructure layer |
| `personality-current` | Python, FastMCP, psn CLI v0.1.9a5 | **Most Advanced** | Full MCP server with SQLite, zip pcart format |
| `claude-plugins/personality` | Python | Active | Plugin snapshot (same as personality) |
| `Legacy/personality-hooks` | Python, shell hooks | Legacy | Early prototype with proxy/hook system |
| `Legacy/personality-cartridge` | Ruby, Rumale ML | Legacy | **Most complete** - real ML training |
| `Legacy/personality-gem` | Ruby, MCP+ACP | Legacy | Dual protocol, rich memory services |
| `Legacy/personality-mcp` | Python, PostgreSQL | Legacy | Full Python rewrite, **9 training personas** |
| `Legacy/personality-plugin` | Python, FastMCP, SQLModel | Legacy | Precursor to personality-current |
| `Legacy/personality-proto` | Ruby/Python | Legacy | Original prototype |

---

## The .pcart Format

### Ruby Era (Directory-based)
```
glados.pcart/
  core.yml              # Immutable personality definition
  preferences.yml       # User overrides, memories, TTS config
  conceptual_framework.yml
  descriptions.yml      # Rich identity with quotes
  greetings.yml         # Templated phrases: "Good {{TIME_GREETING}}, Subject {{USER_ID}}"
  exclamations.yml
  avatar.gif
  training_data/        # daily_YYYY-MM-DD.json
  models/               # Serialized ML models (.marshal)
  metadata.yml
```

### Python Era (Zip-based)
```
glados.pcart (zip archive)
  persona.yml           # Core identity and memories
  preferences.yml       # User overrides (NEVER overwritten)
```

**Canonical spec:** `/Users/chi/Projects/Legacy/personality-cartridge/docs/specifications/PCART.md`

---

## Training Personas Available

### In personality-mcp (9 personas):
| Persona | Source | File |
|---------|--------|------|
| GLaDOS | Portal | `GLADOS.yml` + `.jsonld` |
| Tachikoma | Ghost in the Shell | `TACHIKOMA.yml` + `.jsonld` |
| HAL 9000 | 2001: A Space Odyssey | `HAL.yml` + `.jsonld` |
| SHODAN | System Shock | `SHODAN.yml` + `.jsonld` |
| KITT | Knight Rider | `KITT.yml` + `.jsonld` |
| JARVIS | Iron Man | `JARVIS.yml` + `.jsonld` |
| LCARS | Star Trek | `LCARS.yml` + `.jsonld` |
| FRIDAY | Iron Man | `FRIDAY.yml` + `.jsonld` |
| BT-7274 | Titanfall 2 | `BT7274.yml` |

### Memory Subject Taxonomy (dot-notation):
- `user.identity.*` - how to address the user
- `self.identity.*` - persona's name, form, origin
- `self.trait.*` - personality characteristics
- `self.belief.*` - worldview and philosophy
- `self.speech.*` - communication patterns (sarcasm level, etc.)
- `self.capability.*` - what the persona can do
- `self.quote.*` - iconic lines verbatim
- `meta.system.*` - TTS mode, config

### Voice Models Found:
- `/Users/chi/Projects/Legacy/personality-hooks/piper/BT7274.onnx` - actual Piper voice model

---

## ML Training (Ruby Era)

The `personality-cartridge` repo has real ML training using **Rumale**:

**Four models per cartridge:**
1. `speech_pattern` - Logistic Regression (friendly, formal, stutter, default)
2. `enthusiasm` - Ridge Regression (0.0-1.0 scale)
3. `verbosity` - Ridge Regression (0.0-1.0 scale)
4. `stutter` - Logistic Regression

**Pipeline:** TF-IDF features + trait values → 80/20 split → serialized as `.marshal`

**Key files:**
- `personality-cartridge/lib/personality/training/orchestrator.rb`
- `personality-cartridge/lib/personality/training/feature_processor.rb`

---

## What Current Plugin is Missing

### vs personality-current:
1. No cartridge/persona loading
2. No training data
3. No persona builder (instruction injection)
4. No knowledge graph
5. No decision tracking
6. Remote-only memory (SSH to junkpile)

### vs Legacy repos:
1. No ML/adaptive learning
2. No ACP server (multi-agent)
3. No dialogue generator / sound filter
4. No memory consolidator/pruner
5. No greeting system with placeholders
6. No avatar support
7. No intent classifier
8. No proactive suggester

---

## Code to Port

### Priority 1: Training Data
```
/Users/chi/Projects/Legacy/personality-mcp/training/
├── GLADOS.yml + .jsonld
├── TACHIKOMA.yml + .jsonld
├── HAL.yml + .jsonld
├── SHODAN.yml + .jsonld
├── KITT.yml + .jsonld
├── JARVIS.yml + .jsonld
├── LCARS.yml + .jsonld
├── FRIDAY.yml + .jsonld
└── BT7274.yml
```

### Priority 2: Persona System
```
/Users/chi/Projects/Legacy/personality-mcp/src/personality/services/
├── training_parser.py      # YAML+JSON-LD parser
├── persona_builder.py      # Instruction builder from memories
└── schemas/training.py     # TrainingDocument/TrainingMemory
```

### Priority 3: Cart Management
```
/Users/chi/Projects/Legacy/personality-plugin/src/personality/services/
├── cart_registry.py        # Cart listing
├── cart_manager.py         # Cart loading from zip
└── db/models.py            # SQLModel schema
```

### Priority 4: Voice Model
```
/Users/chi/Projects/Legacy/personality-hooks/piper/
├── BT7274.onnx             # Actual Piper voice
└── BT7274.onnx.json
```

---

## Evolution Timeline

```
personality-proto (Ruby, ~2024)
    ↓
personality-cartridge (Ruby, ML training, most complete)
    ↓
personality-gem (Ruby, ACP, rich memory)
    ↓
personality-hooks (Python, proxy approach)
    ↓
personality-mcp (Python, PostgreSQL, 9 personas)
    ↓
personality-plugin (Python, FastMCP, 1024-dim)
    ↓
personality-current (Python, zip pcarts, session aware)
    ↓
personality (current plugin - infrastructure only)
```

---

## Recommendations

1. **Copy training data** from `personality-mcp/training/` to current plugin
2. **Port training_parser.py** and **persona_builder.py** for persona loading
3. **Add cart registry** for managing multiple personas
4. **Wire SessionStart hook** to inject persona instructions
5. **Copy BT7274.onnx** voice model to voices directory
6. **Consider porting** memory consolidator/pruner pattern from personality-gem
7. **Evaluate** whether ML training (Rumale-style) is worth porting to Python

---

## Files of Interest

| Purpose | Path |
|---------|------|
| .pcart spec | `Legacy/personality-cartridge/docs/specifications/PCART.md` |
| Training parser | `Legacy/personality-mcp/src/personality/services/training_parser.py` |
| Persona builder | `Legacy/personality-mcp/src/personality/services/persona_builder.py` |
| All 9 personas | `Legacy/personality-mcp/training/*.yml` |
| Cart manager | `Legacy/personality-plugin/src/personality/services/cart_manager.py` |
| SQLModel schema | `Legacy/personality-plugin/src/personality/db/models.py` |
| BT-7274 voice | `Legacy/personality-hooks/piper/BT7274.onnx` |
| Ruby ML training | `Legacy/personality-cartridge/lib/personality/training/orchestrator.rb` |
