---
name: cf:del-tunnel
description: Delete a Cloudflare Tunnel
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: name
    description: Tunnel name or ID
    required: true
---

# Delete Cloudflare Tunnel

Delete a Cloudflare Tunnel.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Delete tunnel", activeForm: "Deleting tunnel...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/del-tunnel.sh <name>
   ```

3. **Complete and confirm**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show deletion confirmation

## Example

User: `/cf:del-tunnel my-tunnel`

Claude shows spinner: "Deleting tunnel..."
Then: `Tunnel deleted: my-tunnel`

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:add-tunnel`, `/cf:list-tunnels`
