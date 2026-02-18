---
name: cf:del-host
description: Delete DNS record from Cloudflare zone
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: zone
    description: Domain name (e.g., example.com)
    required: true
  - name: record-id
    description: DNS record ID (get from /cf:zone-info)
    required: true
---

# Delete DNS Record

Delete a DNS record from a Cloudflare zone.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Delete DNS record", activeForm: "Deleting DNS record...")
   ```

2. **Execute command** (prompts for confirmation):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/del-host.sh <zone> <record-id>
   ```

3. **Complete and confirm**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show deletion confirmation

## Example

User: `/cf:del-host tengu.host abc123`

Claude shows spinner: "Deleting DNS record..."
Then:

```
DNS record deleted

Zone: tengu.host
Record ID: abc123
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:add-host`, `/cf:zone-info`
