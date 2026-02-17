---
description: Deploy to Cloudflare Pages
arguments:
  - name: directory
    description: Build output directory to deploy
    required: true
  - name: project
    description: Pages project name (created if not exists)
    required: true
  - name: branch
    description: Branch name for deployment
    default: "main"
---
```bash
${CLAUDE_PLUGIN_ROOT}/commands/cf/pages_deploy.sh $ARGUMENTS
```
