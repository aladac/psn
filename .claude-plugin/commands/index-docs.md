---
name: index:docs
description: Index documentation for semantic search
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__indexer__index_docs
  - mcp__indexer__status
  - Glob
argument-hint: "[path] [--project name]"
---

# Index Docs

Index documentation files for semantic search.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Index docs", activeForm: "Indexing documentation...")
   ```

2. **Determine scope**:
   - Use provided path or look for docs/, doc/, README.md
   - Get project name from --project flag or directory name

3. **Index files**:
   - Call indexer for documentation
   - Process markdown, text, rst, adoc files

4. **Complete and summarize**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show clean summary

## Supported Formats

`.md`, `.txt`, `.rst`, `.adoc`

## Example

User: `/index:docs ~/Projects/api/docs`

Claude shows spinner: "Indexing documentation..."
Then:

```
Indexed documentation

45 document chunks
- 12 markdown files
- 3 text files

Search with: /index:search <query>
```

## Related
- **Skill**: `Skill(skill: "psn:indexer")` - Indexing best practices
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:code-analyzer` - Deep code analysis
- **Commands**: `/index:code`, `/index:status`
