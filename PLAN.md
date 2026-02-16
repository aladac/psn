# Plan: Personality Cartridge System

Restore the full persona/cartridge system from legacy repos into the current plugin.

## Phase 1: Training Data & Parser

### Description
Port the 9 training personas from `personality-mcp` and implement YAML parser. This establishes the foundation for persona loading without changing the existing infrastructure.

### Steps

#### Step 1.1: Copy Training Data
- **Objective**: Bring all 9 persona YAML files into current plugin
- **Files**:
  - `training/GLADOS.yml`
  - `training/TACHIKOMA.yml`
  - `training/HAL.yml`
  - `training/SHODAN.yml`
  - `training/KITT.yml`
  - `training/JARVIS.yml`
  - `training/LCARS.yml`
  - `training/FRIDAY.yml`
  - `training/BT7274.yml`
- **Dependencies**: None
- **Implementation**:
  - Copy from `Legacy/personality-mcp/training/`
  - Verify YAML syntax is valid
  - Create `training/README.md` documenting format

#### Step 1.2: Implement Training Parser
- **Objective**: Parse YAML training files into Python dataclasses
- **Files**:
  - `src/personality/schemas/training.py`
  - `src/personality/services/training_parser.py`
- **Dependencies**: Step 1.1
- **Implementation**:
  - Port `TrainingDocument`, `TrainingMemory` schemas from personality-mcp
  - Port `training_parser.py` with YAML loading
  - Add unit tests for parser

#### Step 1.3: Add Persona CLI Commands
- **Objective**: CLI commands to list and inspect personas
- **Files**:
  - `src/personality/cli/persona.py`
  - `src/personality/cli/__init__.py`
- **Dependencies**: Step 1.2
- **Implementation**:
  - `psn persona list` - list available training files
  - `psn persona show <name>` - display persona details
  - `psn persona validate <name>` - validate YAML syntax

## Phase 2: Cartridge System

### Description
Implement the .pcart zip format for packaging personas with user preferences. Support loading, switching, and persisting active persona.

### Steps

#### Step 2.1: Define Pcart Schema
- **Objective**: Python dataclasses for pcart structure
- **Files**:
  - `src/personality/schemas/pcart.py`
- **Dependencies**: Step 1.2
- **Implementation**:
  - `PersonaConfig` dataclass (from persona.yml)
  - `PreferencesConfig` dataclass (from preferences.yml)
  - `Cartridge` dataclass combining both

#### Step 2.2: Implement Cart Manager
- **Objective**: Load/save pcart zip files
- **Files**:
  - `src/personality/services/cart_manager.py`
- **Dependencies**: Step 2.1
- **Implementation**:
  - Port from `Legacy/personality-plugin/src/personality/services/cart_manager.py`
  - `load_cart(path)` - read zip, parse YAML files
  - `save_cart(cart, path)` - write zip with persona.yml + preferences.yml
  - `create_cart_from_training(training_file)` - bootstrap pcart from training YAML

#### Step 2.3: Implement Cart Registry
- **Objective**: Track available and active cartridges
- **Files**:
  - `src/personality/services/cart_registry.py`
  - `carts/` directory
- **Dependencies**: Step 2.2
- **Implementation**:
  - Scan `carts/` directory for .pcart files
  - Track active cart in `current_cart.toml`
  - `switch_persona(name)` method

#### Step 2.4: Add Cart CLI Commands
- **Objective**: CLI for cart management
- **Files**:
  - `src/personality/cli/cart.py`
- **Dependencies**: Step 2.3
- **Implementation**:
  - `psn cart list` - list installed carts
  - `psn cart create <training>` - create pcart from training file
  - `psn cart switch <name>` - switch active persona
  - `psn cart show` - show active persona details

## Phase 3: Persona Builder

### Description
Generate LLM instruction text from loaded persona memories. Inject persona context at session start via hook.

### Steps

#### Step 3.1: Implement Persona Builder
- **Objective**: Convert memories to instruction prompt
- **Files**:
  - `src/personality/services/persona_builder.py`
- **Dependencies**: Step 2.3
- **Implementation**:
  - Port from `Legacy/personality-mcp/src/personality/services/persona_builder.py`
  - Group memories by subject prefix (self.identity, self.trait, etc.)
  - Generate structured prompt with identity, traits, speech patterns
  - Support greeting templates with `{{USER_ID}}`, `{{TIME_GREETING}}`

#### Step 3.2: Wire SessionStart Hook
- **Objective**: Inject persona prompt at session start
- **Files**:
  - `src/personality/cli/hooks.py`
  - `prompts/intro.md`
- **Dependencies**: Step 3.1
- **Implementation**:
  - Update `session_start()` to load active cart
  - Call persona builder to generate prompt
  - Output combined intro + persona prompt
  - Handle case when no cart is active (fallback to basic intro)

#### Step 3.3: Add TTS Integration
- **Objective**: Use persona's preferred voice for TTS
- **Files**:
  - `src/personality/services/cart_manager.py`
  - `src/personality/cli/tts.py`
- **Dependencies**: Step 3.1
- **Implementation**:
  - Read `tts.voice` from persona preferences
  - Auto-switch voice when persona changes
  - Add `psn tts current` to show active voice

## Phase 4: Knowledge Graph

### Description
Add subject-predicate-object triple storage for structured knowledge. Enable semantic queries across persona knowledge.

### Steps

#### Step 4.1: Add Knowledge Table
- **Objective**: Database schema for knowledge triples
- **Files**:
  - `src/personality/cli/index.py` (add table creation)
  - `src/personality/schemas/knowledge.py`
- **Dependencies**: None (parallel to Phase 2-3)
- **Implementation**:
  - Create `knowledge` table: id, subject, predicate, object, project, embedding, created_at
  - Add vector index on embedding column
  - Create `KnowledgeTriple` dataclass

#### Step 4.2: Implement Knowledge Service
- **Objective**: CRUD operations for knowledge triples
- **Files**:
  - `src/personality/services/knowledge.py`
- **Dependencies**: Step 4.1
- **Implementation**:
  - `add_knowledge(subject, predicate, object)`
  - `query_knowledge(subject=None, predicate=None)`
  - `search_knowledge(query)` - semantic search

#### Step 4.3: Add Knowledge CLI
- **Objective**: CLI for knowledge management
- **Files**:
  - `src/personality/cli/knowledge.py`
- **Dependencies**: Step 4.2
- **Implementation**:
  - `psn knowledge add "X" "is a" "Y"`
  - `psn knowledge query --subject "X"`
  - `psn knowledge search "query"`
  - `psn knowledge list`

## Phase 5: Decision Tracking

### Description
Track architectural decisions with rationale, alternatives considered, and outcome. Integrate with project context.

### Steps

#### Step 5.1: Add Decision Table
- **Objective**: Database schema for decisions
- **Files**:
  - `src/personality/cli/index.py`
  - `src/personality/schemas/decision.py`
- **Dependencies**: None (parallel)
- **Implementation**:
  - Create `decisions` table: id, title, context, decision, rationale, alternatives, status, project, created_at
  - Create `Decision` dataclass

#### Step 5.2: Implement Decision Service
- **Objective**: CRUD for decisions
- **Files**:
  - `src/personality/services/decision.py`
- **Dependencies**: Step 5.1
- **Implementation**:
  - `record_decision(title, context, decision, rationale, alternatives)`
  - `list_decisions(project=None, status=None)`
  - `update_decision(id, status)`

#### Step 5.3: Add Decision CLI
- **Objective**: CLI for decision tracking
- **Files**:
  - `src/personality/cli/decision.py`
- **Dependencies**: Step 5.2
- **Implementation**:
  - `psn decision record "Title"` - interactive decision recording
  - `psn decision list` - list decisions
  - `psn decision show <id>` - show decision details

## Phase 6: Memory Management

### Description
Add memory consolidation and pruning to manage context budget. Extract learnings from conversations and consolidate related memories.

### Steps

#### Step 6.1: Implement Memory Extractor
- **Objective**: Extract learnings from conversation transcripts
- **Files**:
  - `src/personality/services/memory_extractor.py`
- **Dependencies**: Existing memory system
- **Implementation**:
  - Parse transcript for user corrections, preferences, facts
  - Categorize by subject taxonomy (user.*, self.*, project.*)
  - Dedupe against existing memories

#### Step 6.2: Implement Memory Consolidator
- **Objective**: Merge related memories to reduce count
- **Files**:
  - `src/personality/services/memory_consolidator.py`
- **Dependencies**: Step 6.1
- **Implementation**:
  - Find memories with similar subjects
  - Merge content while preserving key facts
  - Update embeddings for merged memories

#### Step 6.3: Implement Memory Pruner
- **Objective**: Remove stale or low-value memories
- **Files**:
  - `src/personality/services/memory_pruner.py`
- **Dependencies**: Step 6.2
- **Implementation**:
  - Score memories by recency, access count, relevance
  - Archive low-score memories (don't delete)
  - Set configurable retention policy

#### Step 6.4: Wire PreCompact Hook
- **Objective**: Consolidate/prune before context compression
- **Files**:
  - `hooks/hooks.json`
  - `src/personality/cli/memory.py`
- **Dependencies**: Steps 6.1-6.3
- **Implementation**:
  - Add `psn memory consolidate` command
  - Update PreCompact hook to run consolidation
  - Log consolidation results

## Phase 7: Voice Models

### Description
Add character voice models and integrate with TTS system.

### Steps

#### Step 7.1: Copy Voice Models
- **Objective**: Bring BT7274 voice into plugin
- **Files**:
  - `voices/BT7274.onnx`
  - `voices/BT7274.onnx.json`
- **Dependencies**: None
- **Implementation**:
  - Copy from `Legacy/personality-hooks/piper/`
  - Update `psn tts voices` to scan `voices/` directory
  - Document voice model format

#### Step 7.2: Add Voice Download Command
- **Objective**: Download character voices from HuggingFace
- **Files**:
  - `src/personality/cli/tts.py`
- **Dependencies**: Step 7.1
- **Implementation**:
  - `psn tts download-character hal9000` - download from HF
  - Support HAL, GLaDOS, JARVIS from doc/tts-voices.md
  - Validate downloaded files

#### Step 7.3: Wire Persona Voice Switching
- **Objective**: Auto-switch voice when persona changes
- **Files**:
  - `src/personality/services/cart_manager.py`
- **Dependencies**: Steps 7.1, 2.3
- **Implementation**:
  - Read `tts.voice` from active cart preferences
  - Switch default voice on cart switch
  - Fallback to en_US-lessac-medium if voice not found
