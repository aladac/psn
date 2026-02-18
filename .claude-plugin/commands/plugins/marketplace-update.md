---
name: plugins:marketplace-update
description: Update Claude Code marketplace plugin manifests
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: marketplace
    description: Marketplace name to update (optional - updates all if omitted)
    required: false
---

# Update Marketplace

Update marketplace plugin manifests to get latest available plugins.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Update marketplace", activeForm: "Fetching manifests...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/plugins/marketplace-update.sh [marketplace]
   ```

3. **Complete and show results**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show update summary

## Arguments

- `marketplace` - Optional marketplace name
  - If omitted, updates all configured marketplaces

## Example

User: `/plugins:marketplace-update`

Claude shows spinner: "Fetching manifests..."
Then:

```
Marketplaces updated

official: 45 plugins (3 new)
community: 128 plugins (12 new)
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin guide
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:list`, `/plugins:install`
