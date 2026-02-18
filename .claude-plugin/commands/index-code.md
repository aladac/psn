---
name: index:code
description: Index a codebase for semantic search
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__indexer__index_code
  - mcp__indexer__status
  - Glob
argument-hint: "[path] [--project name]"
---

# Index Code

Index code files in a directory for semantic search.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Index code", activeForm: "Indexing codebase...")
   ```

2. **Determine scope**:
   - Use provided path or current working directory
   - Get project name from --project flag or directory name

3. **Index files**:
   - Call indexer with path and project
   - Update spinner with progress if available

4. **Complete and summarize**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show clean summary with counts

## Supported Languages

`.py`, `.rs`, `.rb`, `.js`, `.ts`, `.go`, `.java`, `.c`, `.cpp`, `.h`

## Example

User: `/index:code ~/Projects/api --project my-api`

Claude shows spinner: "Indexing codebase..."
Then:

```
Indexed 'my-api'

247 code chunks indexed
- 89 Python files
- 34 TypeScript files
- 12 SQL files

Search with: /index:search <query>
```

## Related
- **Skill**: `Skill(skill: "psn:indexer")` - Indexing best practices
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:code-analyzer` - Deep code analysis
- **Commands**: `/index:docs`, `/index:status`
