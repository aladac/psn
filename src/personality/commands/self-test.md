# Self Test

Run diagnostics on all personality systems.

Use the `self_test` MCP tool to check system health.

**Arguments:** $ARGUMENTS

## Systems Checked

- **Cart & Voice**: Active cart configuration, voice model availability
- **Memory System**: Connection status, memory count, subject breakdown
- **Embeddings**: Ollama connection, model, vector dimensions
- **Project Index**: Current project indexing status
- **Docs Index**: Documentation indexing status
- **Arsenal**: Catalogued tool memories from the loadout

## Example Usage

```
/psn:self-test
/psn:self-test --verbose
```

Use `--verbose` to see detailed breakdowns (memory subjects, tool entries).
