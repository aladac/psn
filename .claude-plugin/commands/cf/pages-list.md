---
name: cf:pages-list
description: List Cloudflare Pages projects
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
---

# List Pages Projects

List all Cloudflare Pages projects.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "List Pages", activeForm: "Fetching Pages projects...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/pages-list.sh
   ```

3. **Complete and display**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show formatted project list

## Example

User: `/cf:pages-list`

Claude shows spinner: "Fetching Pages projects..."
Then:

```
Cloudflare Pages Projects

my-blog
  URL: my-blog.pages.dev
  Last deploy: 2 hours ago

docs-site
  URL: docs-site.pages.dev
  Last deploy: 3 days ago
```

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:pages-deploy`, `/cf:pages-destroy`
