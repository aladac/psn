---
description: Delete DNS record from Cloudflare zone
arguments:
  - name: zone
    description: Domain name (e.g., example.com)
    required: true
  - name: record_id
    description: DNS record ID (get from /cf:zone_info)
    required: true
---
```bash
${CLAUDE_PLUGIN_ROOT}/commands/cf/del_host.sh $ARGUMENTS
```
