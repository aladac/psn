---
name: cf:zone-info
description: Get Cloudflare zone details and DNS records
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: zone
    description: Domain name (e.g., example.com)
    required: true
---

# Zone Info

Get Cloudflare zone details and DNS records.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Zone info", activeForm: "Fetching zone details...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/zone-info.sh <zone>
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show zone info and DNS records

## Example

User: `/cf:zone-info tengu.host`

Claude shows spinner: "Fetching zone details..."
Then:

```
Zone: tengu.host

Status: active
Plan: Free
Name Servers: ada.ns.cloudflare.com, bob.ns.cloudflare.com

DNS Records:
  A     @           192.168.1.1    (proxied)
  CNAME www         tengu.host     (proxied)
  TXT   @           "v=spf1..."    (DNS only)
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:list-zones`, `/cf:add-host`, `/cf:del-host`
