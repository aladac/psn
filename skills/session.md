---
description: 'Use this skill when saving or restoring conversation sessions, managing session state, or resuming previous work. Triggers on questions about saving progress, restoring context, or continuing where left off.'
---

# Session Management

Save and restore conversation sessions for seamless work continuity.

## Architecture

Sessions are stored in the memory system:
- **Subject**: `session.{name}`
- **Content**: JSON with full session context
- **Storage**: PostgreSQL with pgvector on junkpile

## Session Structure

```json
{
  "name": "session-name",
  "working_directory": "/path/to/project",
  "timestamp": "2026-02-17T10:30:00Z",
  "context": "Brief description of what was being worked on",
  "open_files": ["src/main.rs", "README.md"],
  "pending_tasks": [
    "Implement pagination",
    "Add tests for new endpoint"
  ],
  "conversation_summary": "Working on API refactor, completed auth module",
  "git_branch": "feature/pagination",
  "notes": "User prefers verbose test output"
}
```

## Saving Sessions

### When to Save
- User explicitly requests: "save this session", "I'll continue later"
- Before context window fills up
- At natural stopping points

### Save Process
1. **Gather context**:
   - Current working directory
   - Git branch (if applicable)
   - Recent files discussed/modified
   - Pending tasks or TODOs
   - Conversation summary
2. **Generate name** (if not provided):
   - Use timestamp: `session-2026-02-17-1030`
   - Or project + date: `api-refactor-feb17`
3. **Store using memory MCP**:
   ```
   Subject: session.{name}
   Content: JSON context object
   Metadata: { timestamp, user, source: "claude-session" }
   ```
4. **Confirm with restore command**

### Save Example
```
User: /session:save morning-work

Gathering session context...
- Working directory: ~/Projects/api
- Branch: feature/auth
- Recent files: src/auth.rs, tests/auth_test.rs
- Pending: Add refresh token support

Session 'morning-work' saved.
Restore with: /session:restore morning-work
```

## Restoring Sessions

### Restore Process
1. **Search memory** for `session.{name}`
2. **If not found**: List available sessions
3. **If found**:
   - Display saved context
   - Change to working directory
   - Summarize pending work
   - Offer to continue

### Restore Example
```
User: /session:restore morning-work

Restoring session 'morning-work'...

📁 Directory: ~/Projects/api
🌿 Branch: feature/auth
📝 Context: Working on API refactor, completed auth module

Pending tasks:
- [ ] Add refresh token support
- [ ] Update API documentation

Continue where you left off?
```

## Listing Sessions

Search for all sessions:
```
Query: "session" with subject filter "session.*"
```

Display as table:
```
| Name          | Date       | Project     |
|---------------|------------|-------------|
| morning-work  | 2026-02-17 | api         |
| bug-fix-123   | 2026-02-16 | frontend    |
| code-review   | 2026-02-15 | shared-lib  |
```

## Session Naming Conventions

| Pattern | Use Case |
|---------|----------|
| `{task}-{date}` | Task-based: `auth-feb17` |
| `{project}-{feature}` | Feature work: `api-pagination` |
| `{ticket}` | Ticket tracking: `JIRA-1234` |
| `{time}` | Quick save: `afternoon-session` |

## Cleanup

Delete old sessions:
```
mcp__memory__forget(id: "session-uuid")
```

Recommended: Clean sessions older than 30 days unless pinned.

## Integration with Memory

Sessions complement the memory system:
- **Sessions**: Temporary work state, restored and discarded
- **Memory**: Persistent knowledge, preferences, patterns

After restoring a session, relevant memories are automatically available through semantic search.

## Best Practices

1. **Name meaningfully** - Use descriptive names you'll recognize later
2. **Save before breaks** - Capture context before stepping away
3. **Include pending tasks** - List what still needs doing
4. **Note blockers** - Record what was blocking progress
5. **Clean up completed** - Remove sessions for finished work
