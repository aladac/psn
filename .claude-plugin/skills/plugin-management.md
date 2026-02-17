---
description: 'Use this skill when managing Claude Code plugins: installing, updating, listing, or working with marketplaces. Triggers on questions about plugin installation, plugin updates, marketplace management, or plugin troubleshooting.'
---

# Plugin Management

Comprehensive guide for managing Claude Code plugins.

## Plugin Architecture

Claude Code plugins are installed to `~/.claude/plugins/` and defined by:

```
~/.claude/plugins/
├── installed/           # Installed plugins (symlinks or copies)
│   ├── psn/            # Example installed plugin
│   └── other-plugin/
└── marketplaces/       # Marketplace manifests
    └── default/        # Default marketplace
```

## Commands

### List Installed Plugins

```bash
/plugins:list
```

Shows all installed plugins with:
- Plugin name and version
- Description
- Source (marketplace or local)
- Status (enabled/disabled)

### Install a Plugin

```bash
/plugins:install <plugin-name>
```

**Arguments:**
- `plugin-name` - Plugin identifier or `marketplace:plugin` format

**Examples:**
```bash
# From default marketplace
/plugins:install awesome-plugin

# From specific marketplace
/plugins:install community:my-plugin

# From local path (use claude CLI)
claude plugin install /path/to/plugin
```

### Update Plugins

```bash
/plugins:update [plugin-name]
```

**Without argument:** Lists plugins with available updates
**With argument:** Updates the specified plugin

**Examples:**
```bash
# Check for updates
/plugins:update

# Update specific plugin
/plugins:update awesome-plugin
```

### Update Marketplace

```bash
/plugins:marketplace-update [marketplace]
```

Refreshes plugin manifests from marketplaces.

**Without argument:** Updates all marketplaces
**With argument:** Updates specific marketplace

**Examples:**
```bash
# Update all marketplaces
/plugins:marketplace-update

# Update specific marketplace
/plugins:marketplace-update community
```

## Plugin Lifecycle

### Discovery
1. Marketplaces provide plugin manifests
2. `plugin marketplace update` fetches latest manifests
3. Browse available plugins in marketplace

### Installation
1. `plugin install <name>` downloads plugin
2. Plugin copied/symlinked to `~/.claude/plugins/installed/`
3. Plugin registered in Claude Code
4. **Restart required** for MCP servers

### Updates
1. Check for version changes in marketplace
2. `plugin update <name>` fetches new version
3. Old version replaced
4. **Restart required** for changes

### Removal
```bash
claude plugin uninstall <plugin-name>
```

## Marketplace Configuration

Marketplaces are configured in `~/.claude/settings.json`:

```json
{
  "plugins": {
    "marketplaces": [
      {
        "name": "default",
        "url": "https://example.com/marketplace"
      },
      {
        "name": "community",
        "url": "https://community.example.com/plugins"
      }
    ]
  }
}
```

## Troubleshooting

### Plugin Not Loading

1. **Check installation:**
   ```bash
   /plugins:list
   ```

2. **Verify structure:**
   - `plugin.json` exists and is valid JSON
   - Required directories present (agents/, skills/, etc.)

3. **Check logs:**
   ```bash
   claude --debug
   ```

### MCP Server Not Available

1. Plugin installed but MCP not working?
2. **Restart Claude Code** - MCP servers require restart
3. Check `mcpServers` section in plugin.json
4. Verify command is in PATH

### Update Failed

1. Check network connectivity
2. Verify marketplace is reachable
3. Check plugin version compatibility
4. Try manual reinstall:
   ```bash
   claude plugin uninstall <plugin>
   claude plugin install <plugin>
   ```

### Marketplace Not Updating

1. Check marketplace URL is valid
2. Verify network access
3. Check for rate limiting
4. Try specific marketplace update:
   ```bash
   /plugins:marketplace-update <name>
   ```

## Best Practices

1. **Keep plugins updated** - Security and bug fixes
2. **Use specific marketplaces** - Know your sources
3. **Restart after MCP changes** - Always restart after plugin changes
4. **Review plugin permissions** - Check what tools plugins request
5. **Backup settings** - Before major updates

## Plugin Development

For creating plugins, use the `claude-admin` agent or invoke these skills:
- `plugin-structure` - Directory layout
- `agent-development` - Creating agents
- `skill-development` - Creating skills
- `command-development` - Creating commands
- `hook-development` - Creating hooks
- `mcp-integration` - Adding MCP servers

## Related Commands

| Command | Description |
|---------|-------------|
| `/plugins:list` | List installed plugins |
| `/plugins:install` | Install a plugin |
| `/plugins:update` | Update plugins |
| `/plugins:marketplace-update` | Refresh marketplace |
