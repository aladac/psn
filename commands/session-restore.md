---
name: session:restore
description: Restore a previously saved session
allowed-tools:
  - mcp__memory__recall
  - mcp__memory__search
  - Read
argument-hint: "<name>"
---

# Session Restore

Restore a previously saved conversation session.

## Instructions

1. If no name provided, list recent sessions and ask user to choose
2. Search memory for session with subject `session.{name}`
3. If found, restore context:
   - Change to the saved working directory
   - Summarize what was being worked on
   - List any pending tasks
   - Offer to continue where left off
4. If not found, inform user and list available sessions

## Example

User: `/session:restore morning-work`

Response: "Session 'morning-work' restored. You were working on the API refactor in ~/Projects/api. Last task: implementing pagination. Continue?"

## Related
- **Skill**: `Skill(skill: "psn:session")` - Session management patterns
- **Commands**: `/session:save`
- **Tools used**: `mcp__memory__recall`, `mcp__memory__search`, `Read`
