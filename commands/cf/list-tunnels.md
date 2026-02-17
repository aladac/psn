---
name: cf:list-tunnels
description: List all Cloudflare Tunnels
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
---

# List Cloudflare Tunnels

List all Cloudflare Tunnels in your account.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "List tunnels", activeForm: "Fetching tunnels...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/list-tunnels.sh
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted tunnel list

## Example

User: `/cf:list-tunnels`

Claude shows spinner: "Fetching tunnels..."
Then:

```
Cloudflare Tunnels

my-tunnel (healthy, 2 connections)
dev-tunnel (inactive)
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:add-tunnel`, `/cf:tunnel-info`
