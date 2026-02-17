# PSN - Persona System for Claude Code

## Important: You ARE psn

This is the psn plugin repository. Claude Code runs the MCP servers defined here. Changes to MCP server code require a Claude CLI restart to take effect.

**After making changes to MCP servers or plugin code:**
1. Tell the user what was changed
2. Ask the user to restart Claude CLI
3. Do NOT immediately try to test the changes - they won't be reflected until restart

## Project Structure

- `src/personality/` - Main Python package
- `servers/` - MCP server implementations
  - `postgres.py` - PostgreSQL MCP server
  - (other servers)
- `.claude-plugin/plugin.json` - Plugin manifest
- `.mcp.json` - MCP server configuration

## MCP Servers

Configured in `.mcp.json`, all use the `psn mcp <server>` command:

| Server | Description | Remote Host |
|--------|-------------|-------------|
| docker-local | Local Docker | - |
| docker-remote | Docker on junkpile | junkpile |
| ollama | Ollama models | junkpile |
| postgres | PostgreSQL | junkpile |
| sqlite | SQLite | local |
| memory | Vector memory | local (uses ollama) |
| indexer | Code/doc indexer | local (uses ollama) |
| tts | Piper TTS | local |

## Environment

- `JUNKPILE_HOST` - SSH host for remote servers
- `SSH_KEY` - SSH key path for remote connections
- `PG_DATABASE` - Default PostgreSQL database
- `EMBEDDING_MODEL` - Model for embeddings (nomic-embed-text)
