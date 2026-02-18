---
name: cf:tunnel-info
description: Get detailed Cloudflare Tunnel information
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: name
    description: Tunnel name or ID
    required: true
---

# Tunnel Info

Get detailed information about a Cloudflare Tunnel.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Tunnel info", activeForm: "Fetching tunnel details...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/tunnel-info.sh <name>
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show tunnel details and routes

## Example

User: `/cf:tunnel-info my-tunnel`

Claude shows spinner: "Fetching tunnel details..."
Then:

```
Tunnel: my-tunnel

ID: abc123-def456
Status: healthy
Connections: 2

Routes:
  api.example.com -> localhost:8080
  web.example.com -> localhost:3000
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:list-tunnels`, `/cf:add-tunnel`
