---
name: session:save
description: Save current session state for later restoration
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__memory__store
  - Bash
argument-hint: "<name> [description]"
---

# Session Save

Save current session state for later restoration.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Save session", activeForm: "Saving session state...")
   ```

2. **Capture state**:
   - Current working directory
   - Git branch and status
   - Recent context from conversation
   - Any pending tasks

3. **Store in memory**:
   - Subject: `session.{name}`
   - Include timestamp and description

4. **Complete and confirm**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show confirmation

## Arguments

- `name` - Session name (required)
- `description` - What you were working on (optional)

## Example

User: `/session:save morning-work implementing pagination`

Claude shows spinner: "Saving session state..."
Then:

```
Session saved: 'morning-work'

Captured:
- Directory: ~/Projects/api
- Branch: feature/pagination
- Context: "implementing pagination"

Restore with: /session:restore morning-work
```

## Related
- **Skill**: `Skill(skill: "psn:session")` - Session patterns
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Commands**: `/session:restore`
