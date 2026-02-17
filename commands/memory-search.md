---
name: memory:search
description: Search memories by subject
allowed-tools:
  - mcp__memory__search
  - mcp__memory__list
argument-hint: "[subject]"
---

# Memory Search

Search memories by subject pattern or list all subjects.

## Instructions

1. If no subject provided, list all memory subjects with counts
2. If subject provided, search for memories matching that subject
3. Display results organized by subject

## Example

User: `/memory:search`

Response:
```
Memory Subjects:
  user.preferences    3 memories
  project.api         12 memories
  tools.docker        5 memories
  session             2 memories
```

User: `/memory:search user.preferences`

Response:
```
Memories in 'user.preferences':
  1. user.preferences.theme - "dark mode preferred"
  2. user.preferences.editor - "uses neovim"
  3. user.preferences.terminal - "kitty with fish shell"
```
