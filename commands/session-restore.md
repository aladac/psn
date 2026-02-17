---
name: session:restore
description: Restore a previously saved session
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__memory__recall
  - mcp__memory__search
  - Bash
argument-hint: "<name>"
---

# Session Restore

Restore a previously saved session.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Restore session", activeForm: "Restoring session...")
   ```

2. **Find session**:
   - Search for `session.{name}` in memory
   - If not found, list available sessions

3. **Restore context**:
   - Change to saved directory
   - Show git status
   - Display saved context and pending tasks

4. **Complete and summarize**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show what was restored

## Arguments

- `name` - Session name to restore

## Example

User: `/session:restore morning-work`

Claude shows spinner: "Restoring session..."
Then:

```
Session restored: 'morning-work'

Directory: ~/Projects/api
Branch: feature/pagination (2 commits ahead)
Context: "implementing pagination for /users endpoint"

Pending tasks:
- Add tests for pagination
- Update API docs
```

## No Session Found

If session doesn't exist:

```
Session 'morning-work' not found

Available sessions:
- afternoon-debug (saved 2 hours ago)
- api-refactor (saved yesterday)
```

## Related
- **Skill**: `Skill(skill: "psn:session")` - Session patterns
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Commands**: `/session:save`
