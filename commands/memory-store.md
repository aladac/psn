---
name: memory:store
description: Store information in persistent memory
allowed-tools:
  - mcp__memory__store
argument-hint: "<subject> <content>"
---

# Memory Store

Store information in persistent memory for later recall.

## Instructions

1. Parse the subject and content from arguments
   - First word/phrase before space is the subject
   - Everything after is the content
2. Call the memory store tool with:
   - subject: The category/topic
   - content: The information to remember
   - metadata: Include timestamp and source context
3. Confirm storage with the memory ID

## Subject Conventions

Use dot notation for hierarchical subjects:
- `user.preferences.editor` - User preferences
- `project.{name}.notes` - Project-specific notes
- `tools.{name}.usage` - Tool usage patterns
- `code.{pattern}.example` - Code patterns

## Example

User: `/memory:store user.preferences.theme dark mode preferred`

Response: "Stored in memory under 'user.preferences.theme' (id: abc123)"
