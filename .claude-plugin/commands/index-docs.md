---
name: index:docs
description: Index documentation for semantic search
allowed-tools:
  - mcp__indexer__index_docs
  - mcp__indexer__status
  - Glob
argument-hint: "[path] [--project name]"
---

# Index Docs

Index documentation files for semantic search.

## Instructions

1. Use provided path or look for common doc directories (docs/, doc/, README.md)
2. Determine project name from --project flag or directory name
3. Call the indexer with appropriate settings
4. Report indexed document count

## Supported Formats

Indexes: `.md`, `.txt`, `.rst`, `.adoc`

## Example

User: `/index:docs ~/Projects/api/docs`

Response:
```
Indexing documentation in ~/Projects/api/docs...

✓ Indexed 45 document chunks
  - 12 markdown files
  - 3 text files

Use `/index:search <query>` to search.
```
