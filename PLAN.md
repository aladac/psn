# Plan: Personality Memory & Context System

Complete implementation of local memory system with Ollama embeddings, sqlite-vec storage, project indexing, MCP prompts, and portable cartridge format.

---

## Phase 1: Ollama Embedder

### Description
Create the local embedding module using Ollama. This is the foundation for all vector operations - memory storage, project indexing, and similarity search.

### Steps

#### Step 1.1: Add Dependencies
- **Objective**: Add ollama and sqlite-vec to project dependencies
- **Files**: `pyproject.toml`
- **Dependencies**: None
- **Implementation**:
  - Add `ollama>=0.4.0` to dependencies
  - Add `sqlite-vec>=0.1.0` to dependencies
  - Add optional `tree-sitter` dependencies for indexing

#### Step 1.2: Create Embedder Module
- **Objective**: Implement Ollama embedding wrapper with caching
- **Files**: `src/personality/memory/embedder.py`, `src/personality/memory/__init__.py`
- **Dependencies**: Step 1.1
- **Implementation**:
  - Create `Embedder` class with `embed()` and `embed_batch()` methods
  - Add `dimensions` property (lazy-evaluated)
  - Add `ensure_model()` to pull model if missing
  - Add `get_embedder()` cached factory function
  - Default model: `nomic-embed-text`

#### Step 1.3: Add Embedder Tests
- **Objective**: Test embedding functionality
- **Files**: `tests/test_embedder.py`
- **Dependencies**: Step 1.2
- **Implementation**:
  - Test single embedding generation
  - Test batch embedding
  - Test dimension consistency
  - Mock Ollama for CI (no GPU required)

---

## Phase 2: Memory Store

### Description
Implement the sqlite-vec based memory storage with hybrid search (vector + full-text). This replaces the pgvector approach from IDEAS.md with a fully embedded solution.

### Steps

#### Step 2.1: Create Database Schema
- **Objective**: Define sqlite-vec schema with FTS5 triggers
- **Files**: `src/personality/memory/schema.py`
- **Dependencies**: Step 1.2
- **Implementation**:
  - Create `memories` table (id, subject, content, source, timestamps)
  - Create `memories_vec` virtual table (vec0)
  - Create `memories_fts` virtual table (FTS5 with porter tokenizer)
  - Add sync triggers for FTS
  - Add indexes on subject and accessed_at

#### Step 2.2: Implement MemoryStore Class
- **Objective**: Create memory store with CRUD and hybrid search
- **Files**: `src/personality/memory/store.py`
- **Dependencies**: Step 2.1
- **Implementation**:
  - Implement `remember(subject, content, source)` - store with embedding
  - Implement `recall(query, k, threshold)` - hybrid vector + FTS search
  - Implement `forget(memory_id)` - delete by ID
  - Implement `consolidate(threshold)` - merge similar memories
  - Implement `list_all()` - get all memories
  - Add `serialize_f32()` helper for vector serialization

#### Step 2.3: Add Memory Store Tests
- **Objective**: Test all memory operations
- **Files**: `tests/test_memory_store.py`
- **Dependencies**: Step 2.2
- **Implementation**:
  - Test remember and recall cycle
  - Test hybrid search ranking
  - Test forget functionality
  - Test consolidate with similar content
  - Test subject hierarchy queries

---

## Phase 3: MCP Memory Tools

### Description
Expose memory operations through the MCP server as tools Claude can invoke. Also add TTS stop functionality.

### Steps

#### Step 3.1: Add stop_speaking Tool
- **Objective**: Allow interruption of TTS playback
- **Files**: `src/personality/speak.py`, `src/personality/mcp/tools.py`
- **Dependencies**: None (existing code)
- **Implementation**:
  - Add `_process` tracking to Speak class
  - Implement `stop()` method with process termination
  - Add PID file for external stop capability
  - Register `stop_speaking` MCP tool

#### Step 3.2: Update AppContext with Memory
- **Objective**: Add MemoryStore to MCP server context
- **Files**: `src/personality/mcp/server.py`
- **Dependencies**: Step 2.2
- **Implementation**:
  - Add `memory: MemoryStore` to AppContext dataclass
  - Initialize memory store in lifespan context
  - Load cart-specific database path from config

#### Step 3.3: Implement Memory Tools
- **Objective**: Add remember, recall, forget, consolidate tools
- **Files**: `src/personality/mcp/tools.py`
- **Dependencies**: Step 3.2
- **Implementation**:
  - Implement `remember(subject, content)` tool
  - Implement `recall(query, limit)` tool
  - Implement `forget(memory_id)` tool
  - Implement `consolidate(threshold)` tool
  - Update speak tool docstring with TTS protocol

#### Step 3.4: Add Memory Resources
- **Objective**: Expose memories via MCP resources
- **Files**: `src/personality/mcp/resources.py`
- **Dependencies**: Step 3.2
- **Implementation**:
  - Add `personality://memories` resource
  - Add `personality://memories/{subject}` resource

#### Step 3.5: Add MCP Memory Tests
- **Objective**: Test MCP memory integration
- **Files**: `tests/test_mcp_memory.py`
- **Dependencies**: Step 3.3
- **Implementation**:
  - Test remember tool via MCP
  - Test recall tool via MCP
  - Test resource access

---

## Phase 4: Hook Integration

### Description
Create CLI hook commands for Claude Code lifecycle events. All hooks call `uv run psn hook <cmd>` directly - no shell scripts.

### Steps

#### Step 4.1: Create Hook CLI Group
- **Objective**: Add `psn hook` command group
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 3.2
- **Implementation**:
  - Add `@cli.group() hook` command group
  - Ensure cart, speak, and memory available in context
  - Add JSON stdin/stdout handling for hook protocol

#### Step 4.2: Implement session-start Hook
- **Objective**: Initialize session with context loading and greeting
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 4.1
- **Implementation**:
  - Load recent context from memory
  - Detect project and load index if available
  - Speak greeting with cart tagline
  - Output JSON with status and context

#### Step 4.3: Implement session-end Hook
- **Objective**: Consolidate memories and farewell
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 4.1
- **Implementation**:
  - Run memory consolidation
  - Speak farewell
  - Output JSON with stats

#### Step 4.4: Implement stop Hook
- **Objective**: Handle Claude stop events
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 4.1
- **Implementation**:
  - Read stop_reason from stdin JSON
  - Speak "Standing by" only on end_turn
  - Silent on tool_use

#### Step 4.5: Implement notify Hook
- **Objective**: Speak notifications
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 4.1
- **Implementation**:
  - Read message from stdin or --message flag
  - Speak notification title

#### Step 4.6: Document Hook Configuration
- **Objective**: Update settings.json example
- **Files**: `CLAUDE.md`
- **Dependencies**: Step 4.5
- **Implementation**:
  - Add hooks section with all four hooks
  - Document timeout values
  - Add mcpServers configuration

---

## Phase 5: Project Indexing

### Description
Index codebases for instant context loading. Uses tree-sitter for semantic chunking and Ollama for embeddings.

### Steps

#### Step 5.1: Create Index Schema
- **Objective**: Define schema for project index database
- **Files**: `src/personality/index/schema.py`, `src/personality/index/__init__.py`
- **Dependencies**: Step 2.1
- **Implementation**:
  - Create `chunks` table (file_path, chunk_type, name, content, lines)
  - Create `chunks_vec` virtual table
  - Create `chunks_fts` virtual table
  - Create `files` table for change detection
  - Create `summary` table for generated summary

#### Step 5.2: Implement Code Chunker
- **Objective**: Parse code into semantic chunks using tree-sitter
- **Files**: `src/personality/index/chunker.py`
- **Dependencies**: Step 5.1
- **Implementation**:
  - Define chunk types per language (function, class, module)
  - Implement `chunk_file(path, language)` with tree-sitter
  - Add `sliding_window_chunks()` fallback
  - Add `detect_language()` helper
  - Support Python, Ruby, Rust, JavaScript, TypeScript

#### Step 5.3: Implement ProjectIndexer
- **Objective**: Index entire projects with embeddings
- **Files**: `src/personality/index/indexer.py`
- **Dependencies**: Step 5.2
- **Implementation**:
  - Implement `index(force)` - scan, chunk, embed, store
  - Implement `search(query, k)` - vector search chunks
  - Implement `_generate_summary()` - create human-readable summary
  - Add file hash tracking for change detection
  - Add registry for path → project_id mapping
  - Respect .gitignore patterns

#### Step 5.4: Add Index CLI Commands
- **Objective**: Add psn index and psn projects commands
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 5.3
- **Implementation**:
  - Add `psn index` - index current directory
  - Add `psn index --force` - re-index from scratch
  - Add `psn index --status` - show freshness
  - Add `psn projects` - list indexed projects
  - Add `psn projects rm <id>` - remove index

#### Step 5.5: Add Project MCP Tools
- **Objective**: Expose project search via MCP
- **Files**: `src/personality/mcp/tools.py`
- **Dependencies**: Step 5.3
- **Implementation**:
  - Implement `project_search(query, limit)` tool
  - Implement `project_summary()` tool
  - Add `personality://project` resource
  - Update session-start hook to load project context

#### Step 5.6: Add Project Index Tests
- **Objective**: Test indexing functionality
- **Files**: `tests/test_index.py`
- **Dependencies**: Step 5.3
- **Implementation**:
  - Test file discovery
  - Test code chunking
  - Test search relevance
  - Test change detection

---

## Phase 6: MCP Prompts

### Description
Implement MCP prompt templates that Claude can request for structured context scaffolding.

### Steps

#### Step 6.1: Create Prompts Module
- **Objective**: Set up prompt registration infrastructure
- **Files**: `src/personality/mcp/prompts.py`
- **Dependencies**: Step 3.2
- **Implementation**:
  - Import FastMCP prompt decorator
  - Set up context access pattern

#### Step 6.2: Implement persona_scaffold Prompt
- **Objective**: Generate full persona context
- **Files**: `src/personality/mcp/prompts.py`
- **Dependencies**: Step 6.1
- **Implementation**:
  - Load cart identity, traits, communication style
  - Fetch self.* memories
  - Format as structured markdown

#### Step 6.3: Implement conversation_starter Prompt
- **Objective**: Initialize with user context
- **Files**: `src/personality/mcp/prompts.py`
- **Dependencies**: Step 6.1
- **Implementation**:
  - Fetch user.* memories
  - Fetch recent session context
  - Format with guidelines

#### Step 6.4: Implement learning_interaction Prompt
- **Objective**: Knowledge extraction template
- **Files**: `src/personality/mcp/prompts.py`
- **Dependencies**: Step 6.1
- **Implementation**:
  - Accept topic parameter
  - Provide subject hierarchy guide
  - Include extraction examples

#### Step 6.5: Implement project_overview Prompt
- **Objective**: Comprehensive project context
- **Files**: `src/personality/mcp/prompts.py`
- **Dependencies**: Step 5.3
- **Implementation**:
  - Load project index summary
  - Fetch project.* memories
  - List available actions

#### Step 6.6: Implement decision_support Prompt
- **Objective**: Structured decision-making
- **Files**: `src/personality/mcp/prompts.py`
- **Dependencies**: Step 6.1
- **Implementation**:
  - Accept decision parameter
  - Fetch relevant memories
  - Provide decision framework

---

## Phase 7: Portable Cartridge Format

### Description
Implement .pcart portable format for exporting and importing personality cartridges with their memories.

### Steps

#### Step 7.1: Define Manifest Schema
- **Objective**: Create manifest.json format
- **Files**: `src/personality/cart/portable.py`, `src/personality/cart/__init__.py`
- **Dependencies**: Step 2.2
- **Implementation**:
  - Define manifest JSON schema
  - Include checksums, version, metadata
  - Track included components (voice, memories)

#### Step 7.2: Implement Core/Preferences Separation
- **Objective**: Split cart into immutable and learned parts
- **Files**: `src/personality/cart/portable.py`
- **Dependencies**: Step 7.1
- **Implementation**:
  - Define core.yml structure (identity, traits, protocols)
  - Define preferences.yml structure (user data, overrides, stats)
  - Implement extraction from existing cart format

#### Step 7.3: Implement Export Functionality
- **Objective**: Export cart to .pcart directory or ZIP
- **Files**: `src/personality/cart/portable.py`
- **Dependencies**: Step 7.2
- **Implementation**:
  - Implement `PortableCart.export(cart_name, output_path)`
  - Copy core.yml, preferences.yml
  - Copy memory.db
  - Optionally copy voice model
  - Generate manifest with checksums
  - Add ZIP archive option

#### Step 7.4: Implement Import Functionality
- **Objective**: Import .pcart with load modes
- **Files**: `src/personality/cart/portable.py`
- **Dependencies**: Step 7.3
- **Implementation**:
  - Implement `PortableCart.load(path)` - from directory or ZIP
  - Implement `install(mode)` with safe/override/merge/dry-run
  - Implement `_merge_memories()` - deduplicate by content hash
  - Implement `_merge_preferences()` - preserve user data

#### Step 7.5: Add Cart CLI Commands
- **Objective**: Add psn cart export/import commands
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 7.4
- **Implementation**:
  - Add `psn cart export <name> -o <path>` command
  - Add `psn cart export --zip` option
  - Add `psn cart import <path> --mode <mode>` command
  - Add `psn cart import --dry-run` option

#### Step 7.6: Add Cart MCP Tools
- **Objective**: Expose cart operations via MCP
- **Files**: `src/personality/mcp/tools.py`
- **Dependencies**: Step 7.4
- **Implementation**:
  - Implement `cart_export(name, include_voice)` tool
  - Implement `cart_import(path, mode)` tool

#### Step 7.7: Add Portable Cart Tests
- **Objective**: Test export/import cycle
- **Files**: `tests/test_portable_cart.py`
- **Dependencies**: Step 7.4
- **Implementation**:
  - Test export creates valid structure
  - Test import with each mode
  - Test memory merge deduplication
  - Test preference preservation

---

## Phase 8: Slash Commands & Documentation

### Description
Update slash commands and documentation to reflect new capabilities.

### Steps

#### Step 8.1: Create New Slash Commands
- **Objective**: Add remember, recall, index commands
- **Files**: `commands/psn/remember.md`, `commands/psn/recall.md`, `commands/psn/index.md`
- **Dependencies**: Step 3.3, Step 5.4
- **Implementation**:
  - Create /psn:remember command template
  - Create /psn:recall command template
  - Create /psn:index command template
  - Update psn install to include new commands

#### Step 8.2: Update CLAUDE.md
- **Objective**: Document new architecture and commands
- **Files**: `CLAUDE.md`
- **Dependencies**: All previous phases
- **Implementation**:
  - Update architecture section
  - Document memory tools and subject hierarchy
  - Document project indexing workflow
  - Document cart portability

#### Step 8.3: Update psn install Command
- **Objective**: Install all new slash commands
- **Files**: `src/personality/cli.py`
- **Dependencies**: Step 8.1
- **Implementation**:
  - Add new command files to install list
  - Update uninstall to remove all

---

## Phase 9: Integration Testing

### Description
End-to-end testing of the complete system.

### Steps

#### Step 9.1: Create Integration Test Suite
- **Objective**: Test full workflows
- **Files**: `tests/test_integration.py`
- **Dependencies**: All previous phases
- **Implementation**:
  - Test session lifecycle (start → work → end)
  - Test memory persistence across sessions
  - Test project index and search
  - Test cart export/import cycle

#### Step 9.2: Performance Testing
- **Objective**: Ensure acceptable latency
- **Files**: `tests/test_performance.py`
- **Dependencies**: Step 9.1
- **Implementation**:
  - Benchmark embedding generation
  - Benchmark memory recall (target: <100ms)
  - Benchmark project search (target: <200ms)
  - Test with large memory databases

#### Step 9.3: CI Configuration
- **Objective**: Set up GitHub Actions
- **Files**: `.github/workflows/test.yml`
- **Dependencies**: Step 9.1
- **Implementation**:
  - Configure Python matrix
  - Mock Ollama for CI
  - Run full test suite
  - Coverage reporting
