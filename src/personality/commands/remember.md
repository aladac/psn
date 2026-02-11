# Remember Information

Store information in the personality memory system for future recall.

Use the `remember` MCP tool to store knowledge with a subject hierarchy.

**Arguments:** $ARGUMENTS

## Subject Hierarchy Guide

Structure information using dot notation:
- `user.name` - User's name
- `user.preferences.*` - User preferences (editor, theme, etc.)
- `project.stack` - Current project's tech stack
- `project.decisions.*` - Architectural decisions
- `self.capabilities.*` - Own capabilities and learnings

## Example Usage

```
/psn:remember user.name The user's name is Pilot Chi
/psn:remember project.stack Python with FastMCP and sqlite-vec
```

If no subject and content provided, ask what I should remember.
