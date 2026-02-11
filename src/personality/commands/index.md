# Project Indexing

Index the current project for semantic code search.

## Commands

### Index Current Project
```bash
psn index
```

### Force Re-index
```bash
psn index --force
```

### Check Index Status
```bash
psn index --status
```

### List Indexed Projects
```bash
psn projects list
```

## MCP Tools

Once indexed, use these MCP tools:
- `project_search(query)` - Search code semantically
- `project_summary()` - Get project overview

## What Gets Indexed

- Python, Ruby, Rust, JavaScript, TypeScript files
- Semantic chunks (functions, classes, modules)
- File hashes for change detection
- Respects .gitignore patterns

## Example Usage

```
/psn:index          # Index current directory
/psn:index --status # Check index freshness
```
