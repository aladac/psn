# MCP Quickstart

## Python Server (FastMCP)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting."""
    return f"Hello, {name}!"

@mcp.prompt()
def review_code(code: str) -> str:
    """Generate a code review prompt."""
    return f"Please review this code:\n\n{code}"

if __name__ == "__main__":
    mcp.run()  # stdio by default
```

**Run:**
```bash
uv run mcp dev server.py        # Dev mode with inspector
uv run mcp install server.py    # Install in Claude Desktop
```

## TypeScript Server

```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const server = new McpServer({
  name: 'demo-server',
  version: '1.0.0',
});

server.tool('add', { a: z.number(), b: z.number() }, async ({ a, b }) => ({
  content: [{ type: 'text', text: String(a + b) }],
}));

server.resource('greeting', 'greeting://{name}', async (uri) => ({
  contents: [{ uri: uri.href, text: `Hello, ${uri.pathname}!`, mimeType: 'text/plain' }],
}));

const transport = new StdioServerTransport();
await server.connect(transport);
```

## Python Client

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="uv",
    args=["run", "server.py"],
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            # Call tool
            result = await session.call_tool("add", {"a": 5, "b": 3})
            print(result.content[0].text)  # "8"

            # Read resource
            from pydantic import AnyUrl
            content = await session.read_resource(AnyUrl("greeting://World"))
            print(content.contents[0].text)  # "Hello, World!"

asyncio.run(main())
```

## Streamable HTTP Server

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HTTPServer", stateless_http=True, json_response=True)

@mcp.tool()
def process(data: str) -> str:
    return f"Processed: {data}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # http://localhost:8000/mcp
```

## Claude Desktop Configuration

`~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "/path/to/server.py"]
    }
  }
}
```

## Claude Code Integration

```bash
# Add stdio server
claude mcp add my-server -- uv run /path/to/server.py

# Add HTTP server
claude mcp add --transport http my-server http://localhost:8000/mcp
```

## Testing with MCP Inspector

```bash
# Python server
uv run mcp dev server.py

# Or standalone inspector
npx @modelcontextprotocol/inspector
```

## Key Concepts

| Primitive | Control | Use Case |
|-----------|---------|----------|
| **Tools** | Model-controlled | Actions, API calls, computations |
| **Resources** | Application-controlled | Data context, file contents |
| **Prompts** | User-controlled | Reusable templates |

## Next Steps

- [Tools Documentation](./tools.md) - Defining executable functions
- [Resources Documentation](./resources.md) - Exposing data sources
- [Transports Documentation](./transports.md) - stdio vs HTTP
- [Python SDK](../source/mcp-python-sdk/) - Full Python reference
- [TypeScript SDK](../source/mcp-typescript-sdk/) - Full TypeScript reference
