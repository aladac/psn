---
name: memory:recall
description: Recall information from persistent memory
allowed-tools:
  - mcp__memory__recall
  - mcp__memory__search
argument-hint: "<query>"
---

# Memory Recall

Recall information from persistent memory using semantic search.

## Instructions

1. Use the query to search memory semantically
2. Return the most relevant memories
3. If subject filter provided (e.g., `user.preferences`), narrow search
4. Present results with:
   - Subject
   - Content summary
   - When it was stored
   - Similarity score

## Example

User: `/memory:recall what theme does the user prefer`

Response:
```
Found 1 relevant memory:

📝 user.preferences.theme (stored 2 hours ago)
   "dark mode preferred"
   Similarity: 0.92
```
