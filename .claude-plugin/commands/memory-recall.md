---
name: memory:recall
description: Recall information from persistent memory
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__memory__recall
argument-hint: "<query> [--subject filter]"
---

# Memory Recall

Recall memories by semantic similarity to a query.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Recall memories", activeForm: "Searching memories...")
   ```

2. **Search memories**:
   - Use query for semantic search
   - Apply subject filter if provided
   - Get top 5 results by default

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted results with subjects and relevance

## Arguments

- `query` - What to search for (semantic)
- `--subject` - Optional filter by subject prefix
- `--limit N` - Number of results (default: 5)

## Example

User: `/memory:recall how I like my code formatted`

Claude shows spinner: "Searching memories..."
Then displays:

```
Found 3 memories:

1. user.preferences.code_style (0.92)
   "Prefers 2-space indentation, no trailing commas"

2. project.api.conventions (0.85)
   "Uses Prettier with default settings"

3. tools.editor.settings (0.78)
   "VS Code with format-on-save enabled"
```

## Related
- **Skill**: `Skill(skill: "psn:memory")` - Memory patterns
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:memory-curator` - Memory cleanup
- **Commands**: `/memory:store`, `/memory:search`
