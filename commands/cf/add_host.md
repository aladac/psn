---
description: Add DNS record to Cloudflare zone
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
```bash
${CLAUDE_PLUGIN_ROOT}/commands/cf/add_host.sh $ARGUMENTS
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations guide
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure agent
- **Commands**: `/cf:del_host`, `/cf:zone_info`, `/cf:list_zones`
- **Executes**: `Bash` (flarectl dns create)
