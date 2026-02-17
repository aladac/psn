---
description: Cloudflare Worker operations (deploy, dev, tail, delete, init)
arguments:
  - name: action
    description: "Action: deploy, dev, tail, delete, init"
    required: true
  - name: name
    description: Worker name (required for tail/delete/init)
---
```bash
${CLAUDE_PLUGIN_ROOT}/commands/cf/worker.sh $ARGUMENTS
```
