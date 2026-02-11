# Recall Information

Search the personality memory system for relevant information.

Use the `recall` MCP tool to retrieve stored knowledge.

**Arguments:** $ARGUMENTS

## Usage

Provide a query to search for relevant memories. The system uses hybrid search combining:
- Vector similarity (semantic meaning)
- Full-text search (keyword matching)

## Example Usage

```
/psn:recall user preferences
/psn:recall project architecture decisions
/psn:recall what do I know about the user
```

Results show:
- Memory ID (for deletion with `forget`)
- Subject hierarchy
- Content
- Relevance score

If no query provided, ask what information to search for.
