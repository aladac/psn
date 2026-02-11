# PHYSICS.md

Claude Code tool and hook reference for the Personality project.

## Personality MCP Commands

Tools exposed by the personality MCP server as Claude perceives them:

- `mcp__personality__speak` - Speak text aloud using the configured personality voice

## Base Claude Code Tools

Core tools available in every Claude Code session:

- `Task` - Launch specialized subagents to handle complex, multi-step tasks autonomously
- `TaskOutput` - Retrieve output from a running or completed background task
- `TaskStop` - Stop a running background task by its ID
- `TaskCreate` - Create a structured task item for tracking work progress
- `TaskGet` - Retrieve a task by its ID from the task list
- `TaskUpdate` - Update a task's status, description, or dependencies
- `TaskList` - List all tasks in the current task list
- `Bash` - Execute shell commands with optional timeout and background execution
- `Read` - Read file contents from the local filesystem, including images and PDFs
- `Write` - Write or overwrite a file on the local filesystem
- `Edit` - Perform exact string replacements in files
- `Glob` - Fast file pattern matching using glob patterns
- `Grep` - Search file contents using regular expressions (ripgrep-based)
- `WebFetch` - Fetch and process content from a URL using AI extraction
- `WebSearch` - Search the web and return results with source links
- `NotebookEdit` - Replace, insert, or delete cells in Jupyter notebooks
- `AskUserQuestion` - Present questions with selectable options to the user
- `Skill` - Execute a registered slash command skill
- `EnterPlanMode` - Transition into planning mode for complex implementation tasks
- `ExitPlanMode` - Signal completion of planning and request user approval
- `ListMcpResourcesTool` - List available resources from configured MCP servers
- `ReadMcpResourceTool` - Read a specific resource from an MCP server by URI

## Browse MCP Commands

Browser automation tools from the browse MCP server:

- `mcp__browse__launch` - Launch browser with headed/headless and viewport options
- `mcp__browse__goto` - Navigate to a URL
- `mcp__browse__back` - Go back in browser history
- `mcp__browse__forward` - Go forward in browser history
- `mcp__browse__reload` - Reload the current page
- `mcp__browse__click` - Click on an element by CSS selector
- `mcp__browse__type` - Type text into an input field
- `mcp__browse__query` - Query elements by CSS selector, returns tag, text, and attributes
- `mcp__browse__url` - Get current URL and page title
- `mcp__browse__html` - Get page HTML content
- `mcp__browse__screenshot` - Take a screenshot of the current page
- `mcp__browse__eval` - Execute JavaScript in the browser context
- `mcp__browse__console` - Get captured console messages from the browser
- `mcp__browse__network` - Get captured network requests and responses
- `mcp__browse__intercept` - Block or mock network requests matching a pattern
- `mcp__browse__errors` - Get captured page errors and unhandled exceptions
- `mcp__browse__metrics` - Get page performance metrics and DOM statistics
- `mcp__browse__a11y` - Get accessibility tree snapshot for the page
- `mcp__browse__dialog` - Configure handling of browser dialogs (alert, confirm, prompt)
- `mcp__browse__cookies` - Get, set, delete, or clear browser cookies
- `mcp__browse__storage` - Manage localStorage or sessionStorage
- `mcp__browse__hover` - Hover over an element to trigger hover states
- `mcp__browse__select` - Select options in a dropdown/select element
- `mcp__browse__keys` - Send keyboard keys or shortcuts
- `mcp__browse__upload` - Upload files to a file input element
- `mcp__browse__scroll` - Scroll the page or element into view
- `mcp__browse__viewport` - Resize the browser viewport
- `mcp__browse__emulate` - Emulate a mobile device
- `mcp__browse__wait` - Wait for a specified time in milliseconds
- `mcp__browse__close` - Close the browser and end the session
- `mcp__browse__session_save` - Save session state to a JSON file
- `mcp__browse__session_restore` - Restore a previously saved session state
- `mcp__browse__favicon` - Generate a complete favicon set from an image
- `mcp__browse__convert` - Convert an image to a different format
- `mcp__browse__resize` - Resize an image to specified dimensions
- `mcp__browse__crop` - Crop a region from an image
- `mcp__browse__compress` - Compress an image to reduce file size
- `mcp__browse__thumbnail` - Create a thumbnail from an image

## Claude Code CLI Hooks

Hooks execute shell scripts at specific points during Claude Code sessions:

### PreToolUse Hooks
- `PreToolUse` - Runs before any tool execution, receives tool name and input as JSON
- `PreToolUse:Read` - Runs before file read operations
- `PreToolUse:Write` - Runs before file write operations
- `PreToolUse:Edit` - Runs before file edit operations
- `PreToolUse:Bash` - Runs before shell command execution
- `PreToolUse:Grep` - Runs before content search operations
- `PreToolUse:Glob` - Runs before file pattern matching
- `PreToolUse:WebSearch` - Runs before web search operations
- `PreToolUse:WebFetch` - Runs before URL fetch operations
- `PreToolUse:Task` - Runs before launching subagents

### PostToolUse Hooks
- `PostToolUse` - Runs after any tool execution completes
- `PostToolUse:Read` - Runs after file read operations complete
- `PostToolUse:Write` - Runs after file write operations complete
- `PostToolUse:Edit` - Runs after file edit operations complete
- `PostToolUse:Bash` - Runs after shell command execution completes
- `PostToolUse:Grep` - Runs after content search completes
- `PostToolUse:Glob` - Runs after file pattern matching completes

### Session Lifecycle Hooks
- `SessionStart` - Runs when a Claude Code session begins
- `SessionEnd` - Runs when a Claude Code session terminates

### Notification Hooks
- `Notification` - Runs when Claude Code would send a notification (e.g., task complete)

### Stop Hooks
- `Stop` - Runs when Claude stops generating (can modify stop reason or inject content)
