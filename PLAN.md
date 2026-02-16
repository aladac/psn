# Plan: MCP Resources & Prompts

Add MCP server capabilities to expose persona data via resources and reusable prompt templates.

## Phase 1: MCP Server Foundation

### Description
Set up the MCP server infrastructure using the `mcp` Python package. Register server in plugin configuration.

### Steps

#### Step 1.1: Create MCP Server Entry Point
- **Objective**: Initialize MCP server with personality namespace
- **Files**:
  - `src/personality/mcp/__init__.py`
  - `src/personality/mcp/server.py`
- **Dependencies**: None
- **Implementation**:
  - Install `mcp` package, add to pyproject.toml
  - Create Server instance with name "personality"
  - Add stdio transport for Claude Code integration
  - Create `psn mcp serve` command to run server

#### Step 1.2: Register MCP Server in Plugin
- **Objective**: Wire MCP server into plugin.json
- **Files**:
  - `.claude-plugin/plugin.json`
- **Dependencies**: Step 1.1
- **Implementation**:
  - Add `mcpServers` section to plugin.json
  - Configure stdio transport pointing to `psn mcp serve`
  - Test server discovery in Claude Code

## Phase 2: Persona Resources

### Description
Implement MCP resources for persona and cart data access.

### Steps

#### Step 2.1: Implement Current Memories Resource
- **Objective**: Expose current persona's memories via `persona://current/memories`
- **Files**:
  - `src/personality/mcp/resources/persona.py`
- **Dependencies**: Step 1.1
- **Implementation**:
  - Register `persona://current/memories` resource
  - Load active cart from registry
  - Return memories as JSON array with subject, content, source
  - Handle no active cart case gracefully

#### Step 2.2: Implement Current Identity Resource
- **Objective**: Expose persona identity via `persona://current/identity`
- **Files**:
  - `src/personality/mcp/resources/persona.py`
- **Dependencies**: Step 2.1
- **Implementation**:
  - Register `persona://current/identity` resource
  - Return identity fields: name, full_name, type, tagline
  - Include preferences.tts config
  - Return empty/default if no active cart

#### Step 2.3: Implement Current Cart Resource
- **Objective**: Expose full cart details via `persona://current/cart`
- **Files**:
  - `src/personality/mcp/resources/persona.py`
- **Dependencies**: Step 2.1
- **Implementation**:
  - Register `persona://current/cart` resource
  - Return cart manifest, memory count, voice setting
  - Include path to .pcart file
  - List available carts if none active

## Phase 3: System Resources

### Description
Implement MCP resources for system and user information.

### Steps

#### Step 3.1: Implement User Resource
- **Objective**: Expose user details via `persona://user`
- **Files**:
  - `src/personality/mcp/resources/system.py`
- **Dependencies**: Step 1.1
- **Implementation**:
  - Register `persona://user` resource
  - Return uid, gid, username, real name (from pwd/getpass)
  - Return groups (from grp module)
  - Return home directory, shell

#### Step 3.2: Implement Host Resource
- **Objective**: Expose host details via `persona://host`
- **Files**:
  - `src/personality/mcp/resources/system.py`
- **Dependencies**: Step 3.1
- **Implementation**:
  - Register `persona://host` resource
  - Return uname info (system, node, release, version, machine)
  - Return uptime (from /proc/uptime or `uptime` command)
  - Return current datetime, timezone

#### Step 3.3: Implement Current Project Resource
- **Objective**: Expose project details via `persona://current/project`
- **Files**:
  - `src/personality/mcp/resources/project.py`
- **Dependencies**: Step 1.1
- **Implementation**:
  - Register `persona://current/project` resource
  - Detect project root from CLAUDE_PROJECT_DIR or cwd
  - Return project name, path, git branch/status
  - Detect language from pyproject.toml, package.json, Cargo.toml, Gemfile
  - Return framework hints if detectable

## Phase 4: Knowledge Resources

### Description
Implement MCP resource for knowledge graph access.

### Steps

#### Step 4.1: Implement Knowledge Triples Resource
- **Objective**: Expose knowledge graph via `knowledge://triples`
- **Files**:
  - `src/personality/mcp/resources/knowledge.py`
- **Dependencies**: Step 1.1, existing knowledge service
- **Implementation**:
  - Register `knowledge://triples` resource
  - Accept optional query parameters (subject, predicate)
  - Return triples as JSON array
  - Include triple count and last updated timestamp

## Phase 5: MCP Prompts

### Description
Implement reusable prompt templates for persona interactions.

### Steps

#### Step 5.1: Implement Persona Greeting Prompt
- **Objective**: Generate in-character greetings
- **Files**:
  - `src/personality/mcp/prompts/__init__.py`
  - `src/personality/mcp/prompts/persona.py`
- **Dependencies**: Step 1.1, persona_builder service
- **Implementation**:
  - Register `persona-greeting` prompt
  - Accept optional `user_name` argument
  - Use persona_builder to generate greeting
  - Include time-of-day awareness

#### Step 5.2: Implement In-Character Prompt
- **Objective**: Frame questions for in-character responses
- **Files**:
  - `src/personality/mcp/prompts/persona.py`
- **Dependencies**: Step 5.1
- **Implementation**:
  - Register `in-character` prompt
  - Accept `question` argument (required)
  - Load active persona identity and traits
  - Generate prompt instructing Claude to respond in character

#### Step 5.3: Implement Remember Prompt
- **Objective**: Store memories about user/project
- **Files**:
  - `src/personality/mcp/prompts/memory.py`
- **Dependencies**: Step 5.1
- **Implementation**:
  - Register `remember` prompt
  - Accept `subject` and `content` arguments
  - Generate prompt to store as memory
  - Suggest appropriate subject taxonomy

#### Step 5.4: Implement Knowledge Query Prompt
- **Objective**: Query knowledge graph naturally
- **Files**:
  - `src/personality/mcp/prompts/knowledge.py`
- **Dependencies**: Step 5.1
- **Implementation**:
  - Register `knowledge-query` prompt
  - Accept `query` argument
  - Frame as natural language knowledge lookup
  - Include context about available knowledge

## Phase 6: Integration & Testing

### Description
Wire everything together and verify with Claude Code.

### Steps

#### Step 6.1: Add Resource Listing
- **Objective**: Implement list_resources handler
- **Files**:
  - `src/personality/mcp/server.py`
- **Dependencies**: Phases 2-4
- **Implementation**:
  - Register all resources with descriptions
  - Return proper Resource objects with URIs
  - Add mimeType hints (application/json)

#### Step 6.2: Add Prompt Listing
- **Objective**: Implement list_prompts handler
- **Files**:
  - `src/personality/mcp/server.py`
- **Dependencies**: Phase 5
- **Implementation**:
  - Register all prompts with descriptions
  - Define PromptArgument schemas
  - Mark required vs optional arguments

#### Step 6.3: Add MCP CLI Commands
- **Objective**: CLI for testing MCP functionality
- **Files**:
  - `src/personality/cli/mcp.py`
- **Dependencies**: Steps 6.1, 6.2
- **Implementation**:
  - `psn mcp resources` - list available resources
  - `psn mcp read <uri>` - read a resource
  - `psn mcp prompts` - list available prompts
  - `psn mcp prompt <name> [args]` - execute a prompt
