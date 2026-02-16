---
name: index:code
description: Index a codebase for semantic search
allowed-tools:
  - mcp__indexer__index_code
  - mcp__indexer__status
  - Glob
argument-hint: "[path] [--project name]"
---

# Index Code

Index code files in a directory for semantic search.

## Instructions

1. Use provided path or current working directory
2. Determine project name from --project flag or directory name
3. Call the indexer with:
   - path: Directory to index
   - project: Project name for grouping
4. Report progress and final count
5. Note any errors (e.g., binary files, encoding issues)

## Supported Languages

Indexes: `.py`, `.rs`, `.rb`, `.js`, `.ts`, `.go`, `.java`, `.c`, `.cpp`, `.h`

## Example

User: `/index:code ~/Projects/api --project my-api`

Response:
```
Indexing ~/Projects/api as 'my-api'...

✓ Indexed 247 code chunks
  - 89 Python files
  - 34 TypeScript files
  - 12 SQL files

Use `/index:search <query>` to search.
```
