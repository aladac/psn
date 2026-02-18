---
name: cf:worker-info
description: Get Cloudflare Worker details
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: name
    description: Worker name
    required: true
---

# Worker Info

Get detailed information about a Cloudflare Worker.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Worker info", activeForm: "Fetching Worker details...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/worker-info.sh <name>
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show worker details

## Example

User: `/cf:worker-info api-gateway`

Claude shows spinner: "Fetching Worker details..."
Then:

```
Worker: api-gateway

Routes:
  api.example.com/*

Bindings:
  KV: API_CACHE
  D1: api_db

Last deploy: 1 hour ago
Size: 45 KB
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:workers-list`, `/cf:worker`
