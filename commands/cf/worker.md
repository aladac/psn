---
name: cf:worker
description: Cloudflare Worker operations (deploy, dev, tail, delete, init)
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - Bash
arguments:
  - name: action
    description: "Action: deploy, dev, tail, delete, init"
    required: true
  - name: name
    description: Worker name (required for tail/delete/init)
---

# Worker Operations

Manage Cloudflare Workers with various actions.

## Execution Flow

1. **Create task with spinner** (varies by action):
   ```
   TaskCreate(subject: "Worker {action}", activeForm: "{action}ing Worker...")
   ```

2. **Execute command**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/commands/cf/worker.sh <action> [name]
   ```

3. **Complete and show result**:
   ```
   TaskUpdate(taskId: "...", status: "completed")
   ```

## Actions

| Action | Description | Spinner |
|--------|-------------|---------|
| `deploy` | Deploy current directory | "Deploying Worker..." |
| `dev` | Start local dev server | "Starting dev server..." |
| `tail` | Stream live logs | "Streaming Worker logs..." |
| `delete` | Delete a worker | "Deleting Worker..." |
| `init` | Initialize new worker | "Initializing Worker..." |

## Examples

### Deploy
```
/cf:worker deploy
```
Spinner: "Deploying Worker..."

### Tail Logs
```
/cf:worker tail my-worker
```
Spinner: "Streaming Worker logs..."

### Delete
```
/cf:worker delete old-worker
```
Spinner: "Deleting Worker..."

## Related
- **Skill**: `Skill(skill: "psn:cloudflare")` - Cloudflare operations
- **Skill**: `Skill(skill: "psn:pretty-output")` - Output guidelines
- **Agent**: `psn:hostmaster` - Cloudflare infrastructure
- **Commands**: `/cf:workers-list`, `/cf:worker-info`
