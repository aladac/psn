# Claude Code Plugins

Plugins extend Claude Code with custom functionality including slash commands, agents, Skills, hooks, and MCP servers. They can be shared across projects and teams.

## When to Use Plugins vs Standalone Configuration

| Approach | Slash Command Names | Best For |
|----------|-------------------|----------|
| **Standalone** (`.claude/` directory) | `/hello` | Personal workflows, project-specific customizations |
| **Plugins** (`.claude-plugin/plugin.json`) | `/plugin-name:hello` | Sharing with teams, community distribution, versioned releases |

## Plugin Directory Structure

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          (required manifest)
├── commands/                (optional)
│   └── hello.md
├── agents/                  (optional)
├── skills/                  (optional)
│   └── code-review/
│       └── SKILL.md
├── hooks/                   (optional)
│   └── hooks.json
├── .mcp.json               (optional)
└── .lsp.json               (optional)
```

**Important**: Only `plugin.json` goes inside `.claude-plugin/`. All other directories must be at the plugin root level.

## Plugin Manifest Schema

**File**: `.claude-plugin/plugin.json`

```json
{
  "name": "my-first-plugin",
  "description": "A greeting plugin to learn the basics",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier (kebab-case, no spaces) |

### Metadata Fields

| Field | Type | Example |
|-------|------|---------|
| `version` | string | `"2.1.0"` |
| `description` | string | `"Deployment automation tools"` |
| `author` | object | `{"name": "Dev Team", "email": "team@example.com"}` |
| `homepage` | string | `"https://docs.example.com"` |
| `repository` | string | `"https://github.com/user/plugin"` |
| `license` | string | `"MIT"`, `"Apache-2.0"` |
| `keywords` | array | `["deployment", "ci-cd"]` |

### Component Path Fields

| Field | Type | Purpose |
|-------|------|---------|
| `commands` | string\|array | Custom command files/directories |
| `agents` | string\|array | Agent files |
| `skills` | string\|array | Skill directories |
| `hooks` | string\|object | Hook configuration |
| `mcpServers` | string\|object | MCP server definitions |
| `outputStyles` | string\|array | Output style files |
| `lspServers` | string\|object | LSP configuration |

### Complete Manifest Example

```json
{
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://github.com/author"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

## Quickstart: Create Your First Plugin

### Step 1: Create Directory Structure

```bash
mkdir my-first-plugin
mkdir my-first-plugin/.claude-plugin
```

### Step 2: Create Manifest

**File**: `my-first-plugin/.claude-plugin/plugin.json`

```json
{
  "name": "my-first-plugin",
  "description": "A greeting plugin to learn the basics",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

### Step 3: Add Slash Commands

**File**: `my-first-plugin/commands/hello.md`

```markdown
---
description: Greet the user with a personalized message
---

# Hello Command

Greet the user named "$ARGUMENTS" warmly and ask how you can help them today. Make the greeting personal and encouraging.
```

### Step 4: Test Locally

```bash
claude --plugin-dir ./my-first-plugin
```

Then in Claude Code:

```
/my-first-plugin:hello Alex
```

## Plugin Components

### 1. Slash Commands

- **Location**: `commands/` directory
- **Format**: Markdown files (`.md`)
- **Naming**: Filename becomes command name with plugin namespace prefix
- **Placeholders**:
  - `$ARGUMENTS`: Captures all text after the slash command
  - `$1`, `$2`: Individual parameters

**Example**: `commands/review.md` creates `/my-plugin:review`

```markdown
---
description: Greet the user with a personalized message
---

Greet the user named "$ARGUMENTS" warmly.
```

**Individual Parameters**:

```markdown
Analyze the file "$1" and check for "$2" issues.
```

**Invocation**:

```
/my-plugin:analyze src/app.js security
```

### 2. Agents

- **Location**: `agents/` directory
- **Format**: Markdown files describing capabilities

**Structure**:

```markdown
---
description: What this agent specializes in
capabilities: ["task1", "task2", "task3"]
---

# Agent Name

Detailed description...
```

### 3. Skills

- **Location**: `skills/` directory
- **Format**: Directories containing `SKILL.md` files
- **Auto-invoked**: Claude uses them based on task context

**Structure**:

```
skills/
├── pdf-processor/
│   ├── SKILL.md
│   ├── reference.md (optional)
│   └── scripts/ (optional)
└── code-reviewer/
    └── SKILL.md
```

**Example**: `skills/code-review/SKILL.md`

```markdown
---
name: code-review
description: Reviews code for best practices and potential issues. Use when reviewing code, checking PRs, or analyzing code quality.
---

When reviewing code, check for:
1. Code organization and structure
2. Error handling
3. Security concerns
4. Test coverage
```

### 4. Hooks

- **Location**: `hooks/hooks.json`
- **Format**: Event handlers for automation
- **Use Cases**: Post-tool hooks, file watchers, custom workflows

**Available Events**:

- `PreToolUse` / `PostToolUse` / `PostToolUseFailure`
- `PermissionRequest` / `UserPromptSubmit` / `Notification`
- `Stop` / `SubagentStart` / `SubagentStop`
- `SessionStart` / `SessionEnd` / `PreCompact`

**Hook Types**:

- `command`: Execute shell commands/scripts
- `prompt`: LLM evaluation with `$ARGUMENTS` placeholder
- `agent`: Agentic verifier with tools

**Example**: `hooks/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npm run lint:fix $FILE"
          }
        ]
      }
    ]
  }
}
```

### 5. MCP Servers

- **Location**: `.mcp.json`
- **Purpose**: Integration with external tools via Model Context Protocol

**Configuration**:

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    }
  }
}
```

### 6. LSP Servers

- **Location**: `.lsp.json`
- **Purpose**: Language server support for code intelligence
- **Provides**: Diagnostics, navigation, and type information

**Example**:

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

## Plugin Installation Scopes

| Scope | Settings File | Use Case |
|-------|---------------|----------|
| `user` | `~/.claude/settings.json` | Personal plugins (default) |
| `project` | `.claude/settings.json` | Team plugins via version control |
| `local` | `.claude/settings.local.json` | Project-specific, gitignored |
| `managed` | `managed-settings.json` | Read-only managed plugins |

## CLI Commands Reference

### Install Plugin

```bash
claude plugin install <plugin> [options]

Options:
  -s, --scope <scope>  Installation scope (user|project|local) [default: user]
  -h, --help           Display help
```

### Uninstall Plugin

```bash
claude plugin uninstall <plugin> [options]

Aliases: remove, rm
Options:
  -s, --scope <scope>  Uninstall scope [default: user]
```

### Enable Plugin

```bash
claude plugin enable <plugin> [options]

Options:
  -s, --scope <scope>  Scope to enable [default: user]
```

### Disable Plugin

```bash
claude plugin disable <plugin> [options]

Options:
  -s, --scope <scope>  Scope to disable [default: user]
```

### Update Plugin

```bash
claude plugin update <plugin> [options]

Options:
  -s, --scope <scope>  Scope to update (user|project|local|managed) [default: user]
```

### Load Plugin Directory (Session Only)

```bash
# Single plugin
claude --plugin-dir ./my-plugin

# Multiple plugins
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

## Environment Variables

**`${CLAUDE_PLUGIN_ROOT}`**: Absolute path to plugin directory

Use this variable in hooks, MCP servers, and scripts for correct paths regardless of installation location:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/process.sh"
          }
        ]
      }
    ]
  }
}
```

## Converting Standalone Configuration to Plugin

### Step 1: Create Plugin Structure

```bash
mkdir -p my-plugin/.claude-plugin
```

### Step 2: Create Manifest

```json
{
  "name": "my-plugin",
  "description": "Migrated from standalone configuration",
  "version": "1.0.0"
}
```

### Step 3: Copy Existing Files

```bash
cp -r .claude/commands my-plugin/
cp -r .claude/agents my-plugin/
cp -r .claude/skills my-plugin/
```

### Step 4: Migrate Hooks

Create `my-plugin/hooks/hooks.json` with hooks from `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "npm run lint:fix $FILE" }]
      }
    ]
  }
}
```

### Step 5: Test Migration

```bash
claude --plugin-dir ./my-plugin
```

## Plugin Caching and File Resolution

### How Caching Works

- Plugins are copied to a cache directory for security
- Marketplace plugins: entire `source` directory is copied
- Plugins with `.claude-plugin/plugin.json`: root directory is copied

### Path Limitations

- Cannot reference files outside the copied directory
- Use `../` paths that traverse outside plugin root **won't work**

### Solutions for External Dependencies

**Option 1: Use symlinks**

```bash
ln -s /path/to/shared-utils ./shared-utils
```

**Option 2: Restructure marketplace**

```json
{
  "name": "my-plugin",
  "source": "./",
  "description": "Plugin with root-level access",
  "commands": ["./plugins/my-plugin/commands/"],
  "strict": false
}
```

## Debugging and Troubleshooting

### Debug Commands

```bash
claude --debug
```

Shows:
- Plugin loading details
- Manifest validation errors
- Command/agent/hook registration
- MCP server initialization

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Plugin not loading | Invalid `plugin.json` | Validate JSON syntax |
| Commands missing | Wrong directory structure | Ensure `commands/` at root |
| Hooks not firing | Script not executable | Run `chmod +x script.sh` |
| MCP server fails | Missing `${CLAUDE_PLUGIN_ROOT}` | Use variable for paths |
| Path errors | Absolute paths used | Use relative paths with `./` |
| LSP `Executable not found` | Language server not installed | Install binary (e.g., `npm install -g typescript-language-server`) |

### Hook Troubleshooting

1. Check script is executable: `chmod +x ./scripts/your-script.sh`
2. Verify shebang line: `#!/bin/bash` or `#!/usr/bin/env bash`
3. Check path uses `${CLAUDE_PLUGIN_ROOT}`
4. Test script manually: `./scripts/your-script.sh`

## Version Management

Follow semantic versioning (MAJOR.MINOR.PATCH):

```json
{
  "name": "my-plugin",
  "version": "2.1.0"
}
```

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)

**Best practices**:

- Start at `1.0.0` for first stable release
- Update before distributing changes
- Document changes in `CHANGELOG.md`
- Use pre-releases: `2.0.0-beta.1`

## Official Plugin Examples

The official Claude Code repository includes example plugins:

- **agent-sdk-dev**: Interactive setup for new Agent SDK projects
- **feature-dev**: Structured 7-phase workflow for feature development
- **plugin-dev**: Complete toolkit with 8-phase guided plugin creation
- **code-review**: Automated PR reviews using parallel Sonnet agents
- **pr-review-toolkit**: Specialized for comments, tests, error handling
- **security-guidance**: Monitors security patterns during file editing
- **commit-commands**: Streamlines git operations with automated workflows
- **hookify**: Custom hooks to prevent unwanted behaviors
- **frontend-design**: Production-grade UI interfaces

## Sources

- [Claude Code Plugins Guide](https://code.claude.com/docs/en/plugins)
- [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference)
- [GitHub - anthropics/claude-code](https://github.com/anthropics/claude-code)
- [Plugins README on GitHub](https://github.com/anthropics/claude-code/blob/main/plugins/README.md)
