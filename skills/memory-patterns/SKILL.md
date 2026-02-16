---
name: Memory Patterns
description: Use this skill when working with persistent memory, storing information for later recall, or building context across sessions. Triggers on questions about remembering, recalling, storing preferences, or session management.
version: 1.0.0
---

# Memory Patterns

Guidance for effective use of the personality memory system.

## Memory Architecture

The memory system uses:
- **Embeddings**: nomic-embed-text via Ollama on junkpile
- **Storage**: PostgreSQL with pgvector on junkpile
- **Search**: Cosine similarity for semantic recall

## Subject Naming Conventions

Use hierarchical dot notation:

```
user.preferences.{category}     # User preferences
user.workflows.{name}           # User workflow patterns
project.{name}.{aspect}         # Project-specific info
session.{name}                  # Saved sessions
tools.{name}.{aspect}           # Tool usage patterns
code.patterns.{language}        # Code patterns learned
```

## When to Store

Store automatically when:
- User expresses a preference ("I prefer...", "Always use...", "Never...")
- User corrects your behavior
- A solution works well and might be reused
- User explicitly asks to remember something

## When to Recall

Recall proactively when:
- Starting work on a known project
- User asks about past decisions
- Applying learned preferences
- Resuming a saved session

## Memory Lifecycle

1. **Store**: Capture with clear subject and concise content
2. **Recall**: Search semantically, present relevant memories
3. **Update**: Store new version with same subject to update
4. **Forget**: Remove outdated or incorrect memories

## Examples

### Storing a Preference
```
Subject: user.preferences.commit_style
Content: Uses conventional commits with scope, e.g., "feat(api): add endpoint"
```

### Storing a Project Pattern
```
Subject: project.my-api.architecture
Content: Uses hexagonal architecture with ports/adapters in src/ports/ and src/adapters/
```

### Session Save/Restore
```
Subject: session.morning-work
Content: {
  "working_directory": "/Users/chi/Projects/api",
  "context": "Implementing pagination for /users endpoint",
  "pending_tasks": ["Add tests", "Update docs"],
  "timestamp": "2024-01-15T10:30:00Z"
}
```
