---
name: cf:workers-list
description: List Cloudflare Workers
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
---

# List Workers

List all Cloudflare Workers.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "List Workers", activeForm: "Fetching Workers...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/workers-list.sh
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted worker list

## Example

User: `/cf:workers-list`

Claude shows spinner: "Fetching Workers..."
Then:

```
Cloudflare Workers

api-gateway
  Routes: api.example.com/*
  Last deploy: 1 hour ago

image-resizer
  Routes: images.example.com/*
  Last deploy: 2 days ago
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:worker`, `/cf:worker-info`
