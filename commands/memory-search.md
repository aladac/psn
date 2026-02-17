---
name: memory:search
description: Search memories by subject
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - mcp__memory__search
  - mcp__memory__list
argument-hint: "[subject-pattern]"
---

# Memory Search

Search memories by subject pattern or list all subjects.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Search memories", activeForm: "Searching by subject...")
   ```

2. **Execute search**:
   - If pattern given: search by subject
   - If no pattern: list all subjects with counts

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show organized results

## Arguments

- `subject-pattern` - Subject to search (optional)
  - Exact: `user.preferences`
  - Prefix: `user.*` or `project.api.*`

## Examples

### List All Subjects

User: `/memory:search`

```
Memory subjects:

user.preferences (4 memories)
project.api (3 memories)
tools.editor (2 memories)
code.patterns (5 memories)
```

### Search by Subject

User: `/memory:search user.preferences`

```
Memories in 'user.preferences':

1. user.preferences.theme
   "Dark mode preferred"

2. user.preferences.code_style
   "2-space indentation"
```

## Related
- **Skill**: `Skill(skill: "psn:memory")` - Memory patterns
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:memory-curator` - Memory cleanup
- **Commands**: `/memory:store`, `/memory:recall`
