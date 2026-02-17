---
name: plugins:list
description: List installed Claude Code plugins
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
---

# List Plugins

List all installed Claude Code plugins.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "List plugins", activeForm: "Fetching plugins...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/plugins/list.sh
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted plugin list

## Example

User: `/plugins:list`

Claude shows spinner: "Fetching plugins..."
Then:

```
Installed Plugins

psn (v0.2.0)
  Persona system - memory, TTS, indexer

plugin-dev (v1.0.0)
  Plugin development tools
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin guide
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:install`, `/plugins:update`
