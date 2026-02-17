---
name: index:status
description: Show indexing status and statistics
allowed-tools:
  - mcp__indexer__status
argument-hint: "[project]"
---

# Index Status

Show current indexing status and statistics.

## Instructions

1. Call indexer status tool
2. If project specified, filter to that project
3. Display:
   - Total indexed chunks (code and docs)
   - Breakdown by project
   - Last indexed timestamp
   - Index health

## Example

User: `/index:status`

Response:
```
Index Status:

Code Index:
  my-api       247 chunks (last: 2h ago)
  personality   89 chunks (last: 1d ago)

Doc Index:
  my-api        45 chunks (last: 2h ago)
  personality   12 chunks (last: 1d ago)

Total: 393 chunks across 2 projects
```
