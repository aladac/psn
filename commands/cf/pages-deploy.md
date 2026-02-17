---
name: cf:pages-deploy
description: Deploy to Cloudflare Pages
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
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

# Deploy to Pages

Deploy a directory to Cloudflare Pages.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Deploy to Pages", activeForm: "Deploying to Pages...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/pages-deploy.sh <directory> <project> [branch]
   ```

3. **Complete and show URL**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show deployment URL

## Example

User: `/cf:pages-deploy dist my-site main`

Claude shows spinner: "Deploying to Pages..."
Then:

```
Deployed to Cloudflare Pages

Project: my-site
Branch: main
URL: https://abc123.my-site.pages.dev

Production URL: https://my-site.pages.dev
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:pages-list`, `/cf:pages-destroy`
