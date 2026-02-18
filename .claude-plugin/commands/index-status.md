---
name: index:status
description: Show indexing status and statistics
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__indexer__status
argument-hint: "[--project name]"
---

# Index Status

Show indexing status and statistics.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Index status", activeForm: "Fetching index stats...")
   ```

2. **Get status**:
   - Query indexer for statistics
   - Filter by project if specified

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted statistics

## Arguments

- `--project name` - Filter to specific project

## Example

User: `/index:status`

Claude shows spinner: "Fetching index stats..."
Then:

```
Index Status

Projects indexed: 3

my-api
  Code: 247 chunks (89 files)
  Docs: 45 chunks (15 files)
  Last indexed: 2 hours ago

blog
  Code: 124 chunks (42 files)
  Docs: 12 chunks (5 files)
  Last indexed: 1 day ago

Total: 428 chunks
```

## Related
- **Skill**: `Skill(skill: "psn:indexer")` - Indexing best practices
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Commands**: `/index:code`, `/index:docs`
