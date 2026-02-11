# Search Documentation

Search the indexed documentation for relevant content.

Use the `docs_search` MCP tool to find information across markdown docs.

**Arguments:** $ARGUMENTS

## Usage

Provide a search query to find relevant documentation sections. The system uses hybrid search combining:
- Vector similarity (semantic meaning)
- Full-text search (keyword matching)

## Example Usage

```
/psn:docs-search MCP tools
/psn:docs-search authentication patterns
/psn:docs-search error handling
```

Results include:
- Document title
- Section heading
- Content preview
- Source URL (if from fetched docs)
- Relevance score

If not indexed, run `psn docs index` first.
