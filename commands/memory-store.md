---
name: memory:store
description: Store information in persistent memory
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__memory__store
argument-hint: "<subject> <content>"
---

# Memory Store

Store information in persistent memory for later recall.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Store memory", activeForm: "Storing memory...")
   ```

2. **Parse and store**:
   - First word/phrase is the subject
   - Everything after is the content
   - Add metadata with timestamp

3. **Complete and summarize**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show: "Stored in '{subject}'"

## Subject Conventions

Use dot notation for hierarchical subjects:
- `user.preferences.editor` - User preferences
- `project.{name}.notes` - Project-specific notes
- `tools.{name}.usage` - Tool usage patterns
- `code.{pattern}.example` - Code patterns

## Example

User: `/memory:store user.preferences.theme dark mode preferred`

Claude shows spinner: "Storing memory..."
Then: "Stored in 'user.preferences.theme'"

## Related
- **Skill**: `Skill(skill: "psn:memory")` - Memory patterns
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:memory-curator` - Memory cleanup
- **Commands**: `/memory:recall`, `/memory:search`
