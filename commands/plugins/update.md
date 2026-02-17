---
description: Update installed Claude Code plugins
arguments:
  - name: plugin
    description: Plugin name to update (optional - lists plugins if omitted)
    required: false
---

```bash
${CLAUDE_PLUGIN_ROOT}/commands/plugins/update.sh $ARGUMENTS
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin management guide
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:list`, `/plugins:install`, `/plugins:marketplace-update`
- **Executes**: `Bash` (claude plugin update)
