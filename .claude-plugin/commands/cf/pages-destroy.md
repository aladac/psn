---
name: cf:pages-destroy
description: Delete a Cloudflare Pages project
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: project
    description: Pages project name
    required: true
---

# Delete Pages Project

Delete a Cloudflare Pages project.

## Execution Flow

1. **Create task with spinner**:
   ```
   TaskCreate(subject: "Delete Pages project", activeForm: "Deleting Pages project...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/pages-destroy.sh <project>
   ```

3. **Complete and confirm**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```
   Show deletion confirmation

## Example

User: `/cf:pages-destroy old-site`

Claude shows spinner: "Deleting Pages project..."
Then: `Pages project deleted: old-site`

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:pages-list`, `/cf:pages-deploy`
