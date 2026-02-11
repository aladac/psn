# Index Documentation

Index markdown documentation for semantic search.

Use the `docs_index` MCP tool to index a documentation directory.

**Arguments:** $ARGUMENTS

## Usage

By default, indexes `~/Projects/docs`. Optionally specify a different path.

The indexer:
- Parses YAML frontmatter (source URL, fetch date)
- Chunks documents by H2/H3 sections
- Creates vector embeddings for semantic search
- Builds FTS index for keyword search

## Example Usage

```
/psn:docs-index
/psn:docs-index --force
/psn:docs-index --path ~/Projects/docs
```

Use `--force` to re-index all files even if unchanged.
