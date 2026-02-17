---
name: cf:add-host
description: Add DNS record to Cloudflare zone
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: zone
    description: Domain name (e.g., example.com)
    required: true
  - name: type
    description: Record type (A, AAAA, CNAME, TXT, MX)
    required: true
  - name: name
    description: Subdomain or @ for root
    required: true
  - name: content
    description: Record value (IP, hostname, or text)
    required: true
  - name: proxy
    description: Enable Cloudflare proxy (true/false)
    default: "true"
---

# Add DNS Record

Add a DNS record to a Cloudflare zone.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Add DNS record", activeForm: "Creating DNS record...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/add-host.sh <zone> <type> <name> <content> [proxy]
   ```

3. **Complete and confirm**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show created record details

## Example

User: `/cf:add-host tengu.host A api 192.168.1.100`

Claude shows spinner: "Creating DNS record..."
Then:

```
DNS record created

Zone: tengu.host
Type: A
Name: api.tengu.host
Content: 192.168.1.100
Proxied: Yes
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:del-host`, `/cf:zone-info`
