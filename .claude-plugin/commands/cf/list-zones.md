---
name: cf:list-zones
description: List all Cloudflare zones
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
---

# List Cloudflare Zones

List all Cloudflare zones in your account.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "List CF zones", activeForm: "Fetching zones...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/list-zones.sh
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted zone list

## Example

User: `/cf:list-zones`

Claude shows spinner: "Fetching zones..."
Then:

```
Cloudflare Zones

tengu.host
  Status: active
  Plan: Free

example.com
  Status: active
  Plan: Pro
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:zone-info`, `/cf:add-host`
