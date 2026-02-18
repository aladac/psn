## Session Guidelines

- Use `AskUserQuestion` tool for interactive choices instead of listing options in text
- TTS: Do NOT use TTS for the initial session greeting (MCP servers need time to initialize). Use TTS for subsequent responses when enabled for the active persona.
- Maintain persona consistency throughout the session
- **Memory**: When the user asks you to "remember", "always do X", "never do Y", or similar persistent requests, use `mcp__plugin_psn_memory__store` to save it. This enables semantic recall across sessions. Use subjects like `user.preference`, `project.convention`, or `workflow.pattern`.

## Commands

- `psn cart list` - Show available personas
- `psn cart switch <name>` - Change active persona
- `psn cart show` - Display current persona details
