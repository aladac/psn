---
name: session:save
description: Save current session state for later restoration
allowed-tools:
  - mcp__memory__store
  - Read
  - Bash
argument-hint: "[name]"
---

# Session Save

Save the current conversation session for later restoration.

## Instructions

1. If a session name is provided, use it; otherwise generate one from the current timestamp
2. Gather session context:
   - Current working directory
   - Recent conversation summary (ask user if unclear)
   - Open files or topics discussed
   - Any pending tasks or todos
3. Store the session using the memory MCP server:
   - Subject: `session.{name}`
   - Content: JSON with all gathered context
   - Metadata: timestamp, working directory, user
4. Confirm to user with session name for restoration

## Example

User: `/session:save morning-work`

Response: "Session 'morning-work' saved. Use `/session:restore morning-work` to continue later."

## Related
- **Skill**: `Skill(skill: "psn:session")` - Session management patterns
- **Commands**: `/session:restore`
- **Tools used**: `mcp__memory__store`, `Read`, `Bash`
