---
source: https://github.com/anthropics/claude-code/tree/main/plugins/plugin-dev
fetched: 2026-02-17
---

# Claude Code Plugin-Dev Directory

## Directory Structure

```
plugins/plugin-dev/
├── agents/
├── commands/
├── skills/
└── README.md
```

---

## README: Plugin Development Toolkit

A comprehensive toolkit for developing Claude Code plugins with expert guidance on hooks, MCP integration, plugin structure, and marketplace publishing.

### Overview

The plugin-dev toolkit provides **7 specialized skills**:

1. **Hook Development** - Advanced hooks API and event-driven automation
2. **MCP Integration** - Model Context Protocol server integration
3. **Plugin Structure** - Plugin organization and manifest configuration
4. **Plugin Settings** - Configuration patterns using `.claude/plugin-name.local.md` files
5. **Command Development** - Creating slash commands with frontmatter and arguments
6. **Agent Development** - Creating autonomous agents with AI-assisted generation
7. **Skill Development** - Creating skills with progressive disclosure and strong triggers

---

## Guided Workflow Command

### `/plugin-dev:create-plugin`

End-to-end workflow for creating plugins from scratch.

**8-Phase Process:**
1. **Discovery** - Understand plugin purpose and requirements
2. **Component Planning** - Determine needed skills, commands, agents, hooks, MCP
3. **Detailed Design** - Specify each component and resolve ambiguities
4. **Structure Creation** - Set up directories and manifest
5. **Component Implementation** - Create each component using AI-assisted agents
6. **Validation** - Run plugin-validator and component-specific checks
7. **Testing** - Verify plugin works in Claude Code
8. **Documentation** - Finalize README and prepare for distribution

**Usage:**
```shell
/plugin-dev:create-plugin [optional description]

# Examples:
/plugin-dev:create-plugin
/plugin-dev:create-plugin A plugin for managing database migrations
```

---

## Skills Detail

### 1. Hook Development
**Triggers:** "create a hook", "add a PreToolUse hook", "validate tool use", "implement prompt-based hooks", "${CLAUDE_PLUGIN_ROOT}", "block dangerous commands"

**Covers:**
- Prompt-based hooks (recommended) with LLM decision-making
- Command hooks for deterministic validation
- All hook events: `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreCompact`, `Notification`
- Hook output formats and JSON schemas
- Security best practices and input validation
- `${CLAUDE_PLUGIN_ROOT}` for portable paths

**Resources:** Core SKILL.md (1,619 words), 3 example hook scripts, 3 reference docs, 3 utility scripts (`validate-hook-schema.sh`, `test-hook.sh`, `hook-linter.sh`)

---

### 2. MCP Integration
**Triggers:** "add MCP server", "integrate MCP", "configure .mcp.json", "Model Context Protocol", "stdio/SSE/HTTP server", "connect external service"

**Covers:**
- MCP server configuration (`.mcp.json` vs `plugin.json`)
- All server types: stdio (local), SSE (hosted/OAuth), HTTP (REST), WebSocket (real-time)
- Environment variable expansion (`${CLAUDE_PLUGIN_ROOT}`, user vars)
- Authentication patterns: OAuth, tokens, env vars

**Resources:** Core SKILL.md (1,666 words), 3 example configurations, 3 reference docs (server-types ~3,200w, authentication ~2,800w, tool-usage ~2,600w)

---

### 3. Plugin Structure
**Triggers:** "plugin structure", "plugin.json manifest", "auto-discovery", "component organization", "plugin directory layout"

**Covers:**
- Standard plugin directory structure and auto-discovery
- `plugin.json` manifest format and all fields
- Component organization (commands, agents, skills, hooks)
- `${CLAUDE_PLUGIN_ROOT}` usage throughout
- Minimal, standard, and advanced plugin patterns

**Resources:** Core SKILL.md (1,619 words), 3 example structures, 2 reference docs

---

### 4. Plugin Settings
**Triggers:** "plugin settings", "store plugin configuration", ".local.md files", "plugin state files", "read YAML frontmatter", "per-project plugin settings"

**Covers:**
- `.claude/plugin-name.local.md` pattern for configuration
- YAML frontmatter + markdown body structure
- Parsing techniques for bash scripts (sed, awk, grep patterns)
- Temporarily active hooks (flag files and quick-exit)
- Atomic file updates and validation
- Gitignore and lifecycle management

**Resources:** Core SKILL.md (1,623 words), 3 examples, 2 reference docs, 2 utility scripts (`validate-settings.sh`, `parse-frontmatter.sh`)

---

### 5. Command Development
**Triggers:** "create a slash command", "add a command", "command frontmatter", "define command arguments", "organize commands"

**Covers:**
- Slash command structure and markdown format
- YAML frontmatter fields (description, argument-hint, allowed-tools)
- Dynamic arguments and file references
- Bash execution for context
- Command organization and namespacing

**Resources:** Core SKILL.md (1,535 words), 10 complete command examples (review, test, deploy, docs, etc.)

---

### 6. Agent Development
**Triggers:** "create an agent", "add an agent", "write a subagent", "agent frontmatter", "when to use description", "agent examples", "autonomous agent"

**Covers:**
- Agent file structure (YAML frontmatter + system prompt)
- All frontmatter fields (name, description, model, color, tools)
- Description format with blocks for reliable triggering
- System prompt design patterns (analysis, generation, validation, orchestration)
- AI-assisted agent generation using Claude Code's proven prompt
- Validation rules and best practices

**Resources:** Core SKILL.md (1,438 words), 2 examples, 3 reference docs, 1 utility script (`validate-agent.sh`)

---

### 7. Skill Development
**Triggers:** "create a skill", "add a skill to plugin", "write a new skill", "improve skill description", "organize skill content"

**Covers:**
- Skill structure (SKILL.md with YAML frontmatter)
- Progressive disclosure principle (metadata → SKILL.md → resources)
- Strong trigger descriptions with specific phrases
- Writing style (imperative/infinitive form, third person)
- Bundled resources organization (references/, examples/, scripts/)

**Resources:** Core SKILL.md (1,232 words), references, examples using plugin-dev's own skills as templates

---

## Installation

```shell
# Install from marketplace
/plugin install plugin-dev@claude-code-marketplace

# Or for development
cc --plugin-dir /path/to/plugin-dev
```

---

## Development Workflow

```
┌─────────────────────┐
│ Design Structure    │ → plugin-structure skill
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Add Components      │
│ (commands, agents,  │ → All skills provide guidance
│ skills, hooks)      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Integrate Services  │ → mcp-integration skill
│ (MCP servers)       │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Add Automation      │ → hook-development skill
│ (hooks, validation) │ + utility scripts
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Test & Validate     │ → validate-hook-schema.sh
│                     │   test-hook.sh
└─────────────────────┘   hook-linter.sh
```

---

## Utility Scripts

```shell
# Validate hooks.json structure
./validate-hook-schema.sh hooks/hooks.json

# Test hooks before deployment
./test-hook.sh my-hook.sh test-input.json

# Lint hook scripts for best practices
./hook-linter.sh my-hook.sh
```

---

## Features

### Progressive Disclosure (3-Level System)
1. **Metadata** (always loaded): Concise descriptions with strong triggers
2. **Core SKILL.md** (when triggered): Essential API reference (~1,500–2,000 words)
3. **References/Examples** (as needed): Detailed guides, patterns, and working code

---

## Total Content
- **Core Skills**: ~11,065 words across 7 SKILL.md files
- **Reference Docs**: ~10,000+ words of detailed guides
- **Examples**: 12+ working examples
- **Utilities**: 6 production-ready scripts

---

## Best Practices

- **Security First** - Input validation, HTTPS/WSS, env vars for credentials, least privilege
- **Portability** - Use `${CLAUDE_PLUGIN_ROOT}` everywhere, relative paths only
- **Testing** - Validate configs before deployment, test hooks with sample inputs, use `claude --debug`
- **Documentation** - Clear READMEs, documented env vars, usage examples

---

## Metadata
- **Version:** 0.1.0
- **Author:** Daisy Hollman (daisy@anthropic.com)
- **License:** MIT
