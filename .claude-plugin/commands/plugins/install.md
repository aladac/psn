---
name: plugins:install
description: Install a Claude Code plugin from marketplace
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: plugin
    description: Plugin name or marketplace:plugin format
    required: true
---

# Install Plugin

Install a Claude Code plugin from a marketplace.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Install plugin", activeForm: "Installing {plugin}...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/plugins/install.sh <plugin>
   ```

3. **Complete and confirm**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show installation confirmation

## Arguments

- `plugin` - Plugin name or `marketplace:plugin` format
  - `my-plugin` - From default marketplace
  - `custom-market:my-plugin` - From specific marketplace

## Example

User: `/plugins:install code-review`

Claude shows spinner: "Installing code-review..."
Then:

```
Plugin installed: code-review (v1.2.0)

New commands:
  /review:pr - Review pull request
  /review:file - Review file
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin guide
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:list`, `/plugins:update`
