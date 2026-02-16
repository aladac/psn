# TODO: Personality Cartridge System

## Phase 1: Training Data & Parser
- [ ] Step 1.1: Copy Training Data (9 YAML files from Legacy/personality-mcp)
- [ ] Step 1.2: Implement Training Parser (schemas + parser service)
- [ ] Step 1.3: Add Persona CLI Commands (list, show, validate)

## Phase 2: Cartridge System
- [ ] Step 2.1: Define Pcart Schema (PersonaConfig, PreferencesConfig, Cartridge)
- [ ] Step 2.2: Implement Cart Manager (load/save zip files)
- [ ] Step 2.3: Implement Cart Registry (track available/active carts)
- [ ] Step 2.4: Add Cart CLI Commands (list, create, switch, show)

## Phase 3: Persona Builder
- [ ] Step 3.1: Implement Persona Builder (memories → instruction prompt)
- [ ] Step 3.2: Wire SessionStart Hook (inject persona at start)
- [ ] Step 3.3: Add TTS Integration (persona voice switching)

## Phase 4: Knowledge Graph
- [ ] Step 4.1: Add Knowledge Table (subject-predicate-object triples)
- [ ] Step 4.2: Implement Knowledge Service (CRUD + semantic search)
- [ ] Step 4.3: Add Knowledge CLI (add, query, search, list)

## Phase 5: Decision Tracking
- [ ] Step 5.1: Add Decision Table (title, context, rationale, alternatives)
- [ ] Step 5.2: Implement Decision Service (CRUD)
- [ ] Step 5.3: Add Decision CLI (record, list, show)

## Phase 6: Memory Management
- [ ] Step 6.1: Implement Memory Extractor (extract from transcripts)
- [ ] Step 6.2: Implement Memory Consolidator (merge related)
- [ ] Step 6.3: Implement Memory Pruner (archive stale)
- [ ] Step 6.4: Wire PreCompact Hook (consolidate before compression)

## Phase 7: Voice Models
- [ ] Step 7.1: Copy Voice Models (BT7274.onnx)
- [ ] Step 7.2: Add Voice Download Command (HuggingFace character voices)
- [ ] Step 7.3: Wire Persona Voice Switching (auto-switch on cart change)

---

**Total:** 0/22 steps completed
