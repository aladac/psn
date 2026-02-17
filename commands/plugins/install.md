---
description: Install a Claude Code plugin from marketplace
arguments:
  - name: plugin
    description: Plugin name or marketplace:plugin format
    required: true
---

```bash
${CLAUDE_PLUGIN_ROOT}/commands/plugins/install.sh $ARGUMENTS
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin management guide
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:list`, `/plugins:update`, `/plugins:marketplace-update`
- **Executes**: `Bash` (claude plugin install)
