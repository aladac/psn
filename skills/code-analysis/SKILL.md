---
name: Code Analysis
description: Use this skill when analyzing code semantically, searching indexed codebases, or understanding code patterns across projects. Triggers on questions about code search, finding implementations, or understanding codebase structure.
version: 1.0.0
---

# Code Analysis

Guidance for semantic code analysis using the indexer.

## Index Architecture

The indexer uses:
- **Chunking**: Code split into ~2000 char overlapping chunks
- **Embeddings**: nomic-embed-text via Ollama
- **Storage**: PostgreSQL with pgvector
- **Search**: Cosine similarity for semantic matching

## Indexing Best Practices

### When to Index
- New project checkout
- After significant code changes
- Before deep code exploration

### What Gets Indexed
- Code files: `.py`, `.rs`, `.rb`, `.js`, `.ts`, `.go`, `.java`, `.c`, `.cpp`, `.h`
- Doc files: `.md`, `.txt`, `.rst`, `.adoc`

### Project Organization
- Index each project separately with meaningful names
- Re-index periodically to capture changes
- Clear stale indices to save space

## Search Strategies

### Finding Implementations
Query: "function that handles user authentication"
→ Returns code chunks with authentication logic

### Finding Patterns
Query: "error handling with retry logic"
→ Returns examples of retry patterns

### Understanding Architecture
Query: "main entry point and initialization"
→ Returns startup/main code

## Combining with Memory

After analysis, store findings:
```
Subject: project.{name}.architecture
Content: Summary of discovered architecture patterns
```

## Search Tips

1. Use natural language queries - embeddings understand semantics
2. Filter by project for focused results
3. Combine code and doc search for full context
4. Check similarity scores - below 0.7 may be weak matches
