---
name: cf:add-tunnel
description: Create a new Cloudflare Tunnel
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: name
    description: Tunnel name
    required: true
---

# Create Cloudflare Tunnel

Create a new Cloudflare Tunnel.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Create tunnel", activeForm: "Creating tunnel...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/add-tunnel.sh <name>
   ```

3. **Complete and show details**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show tunnel ID and connection info

## Example

User: `/cf:add-tunnel my-tunnel`

Claude shows spinner: "Creating tunnel..."
Then:

```
Tunnel created: my-tunnel

ID: abc123-def456
Status: inactive

Next: Configure tunnel routes
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:del-tunnel`, `/cf:list-tunnels`, `/cf:tunnel-info`
