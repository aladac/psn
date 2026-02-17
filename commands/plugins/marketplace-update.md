---
description: Update Claude Code marketplace plugin manifests
arguments:
  - name: marketplace
    description: Marketplace name to update (optional - updates all if omitted)
    required: false
---

```bash
${CLAUDE_PLUGIN_ROOT}/commands/plugins/marketplace-update.sh $ARGUMENTS
```

## Related
- **Skill**: `Skill(skill: "psn:plugin-management")` - Plugin management guide
- **Agent**: `psn:claude-admin` - Plugin development
- **Commands**: `/plugins:list`, `/plugins:install`, `/plugins:update`
- **Executes**: `Bash` (claude plugin marketplace update)
