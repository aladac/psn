---
name: plugins:update
description: Update installed Claude Code plugins
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: plugin
    description: Plugin name to update (optional - updates all if omitted)
    required: false
---

# Update Plugins

Update installed Claude Code plugins.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Update plugins", activeForm: "Updating plugins...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/plugins/update.sh [plugin]
   ```

3. **Complete and show results**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show update summary

## Arguments

- `plugin` - Optional plugin name to update
  - If omitted, updates all plugins

## Example

User: `/plugins:update`

Claude shows spinner: "Updating plugins..."
Then:

```
Plugins updated

psn: 0.1.9 -> 0.2.0
code-review: (up to date)

1 plugin updated, 1 unchanged
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin guide
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:list`, `/plugins:install`
