# MCP SDK Comparison

## Quick Reference

| Feature | Python SDK | FastMCP | TypeScript SDK |
|---------|------------|---------|----------------|
| Package | `mcp` | `fastmcp` | `@modelcontextprotocol/sdk` |
| Install | `uv add mcp` | `uv add fastmcp` | `npm i @modelcontextprotocol/sdk` |
| Style | Decorator-based | Decorator-based | Method chaining |
| Async | anyio | anyio | Native async/await |
| Schema | Pydantic/TypedDict | Pydantic/TypedDict | Zod |
| Auth | Built-in OAuth | Enterprise providers | Manual |
| Testing | In-memory transport | In-memory + Client | In-memory transport |

## When to Use Each

### Python SDK (`mcp`)
- **Official SDK** from Anthropic
- Standard MCP implementation
- Good for: Protocol-compliant servers, SDK contributors

### FastMCP (`fastmcp`)
- **Production framework** built on Python SDK
- Extended features: composition, proxying, enterprise auth
- Good for: Production apps, enterprise deployments, complex architectures

### TypeScript SDK
- **Official SDK** for Node.js/TypeScript
- Full protocol implementation
- Good for: Node.js apps, TypeScript projects, npm ecosystem

## Code Comparison

### Basic Server

**Python SDK:**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

mcp.run()
```

**FastMCP:**
```python
from fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

mcp.run()
```

**TypeScript:**
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const server = new McpServer({ name: 'demo', version: '1.0.0' });

server.tool('add', { a: z.number(), b: z.number() }, async ({ a, b }) => ({
  content: [{ type: 'text', text: String(a + b) }],
}));

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Resources

**Python SDK:**
```python
@mcp.resource("data://{item_id}")
def get_item(item_id: str) -> str:
    return f"Item: {item_id}"
```

**FastMCP:**
```python
@mcp.resource("data://{item_id}")
def get_item(item_id: str) -> str:
    return f"Item: {item_id}"
```

**TypeScript:**
```typescript
server.resource('data', 'data://{item_id}', async (uri) => ({
  contents: [{ uri: uri.href, text: `Item: ${uri.pathname}`, mimeType: 'text/plain' }],
}));
```

### Authentication

**Python SDK:**
```python
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings

class MyVerifier(TokenVerifier):
    async def verify_token(self, token: str):
        # Validate token
        pass

mcp = FastMCP("Server", token_verifier=MyVerifier(), auth=AuthSettings(...))
```

**FastMCP (Enterprise):**
```python
from fastmcp.server.auth.providers.google import GoogleProvider

auth = GoogleProvider(client_id="...", client_secret="...", base_url="...")
mcp = FastMCP("Server", auth=auth)
```

**TypeScript:**
```typescript
// Manual authentication handling in middleware
const server = new McpServer({ name: 'server', version: '1.0.0' });
// Implement token validation in transport layer
```

### Client Usage

**Python SDK:**
```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async with stdio_client(StdioServerParameters(command="uv", args=["run", "server.py"])) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("add", {"a": 1, "b": 2})
```

**FastMCP:**
```python
from fastmcp import Client

async with Client("server.py") as client:
    result = await client.call_tool("add", {"a": 1, "b": 2})

# Or with config for multiple servers
async with Client({"mcpServers": {"s1": {...}, "s2": {...}}}) as client:
    await client.call_tool("s1_add", {"a": 1, "b": 2})
```

**TypeScript:**
```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'client', version: '1.0.0' });
const transport = new StdioClientTransport({ command: 'node', args: ['server.js'] });
await client.connect(transport);
const result = await client.callTool({ name: 'add', arguments: { a: 1, b: 2 } });
```

### Testing

**Python SDK:**
```python
from mcp.client.memory import create_connected_server_and_client_session

async with create_connected_server_and_client_session(mcp._mcp_server) as (_, client):
    result = await client.call_tool("add", {"a": 1, "b": 2})
```

**FastMCP:**
```python
from fastmcp import Client

async with Client(mcp) as client:  # Pass server directly
    result = await client.call_tool("add", {"a": 1, "b": 2})
```

**TypeScript:**
```typescript
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
await server.connect(serverTransport);
await client.connect(clientTransport);
```

## Feature Matrix

| Feature | Python SDK | FastMCP | TypeScript SDK |
|---------|:----------:|:-------:|:--------------:|
| Tools | ✅ | ✅ | ✅ |
| Resources | ✅ | ✅ | ✅ |
| Prompts | ✅ | ✅ | ✅ |
| Sampling | ✅ | ✅ | ✅ |
| Elicitation | ✅ | ✅ | ✅ |
| Structured Output | ✅ | ✅ | ✅ |
| stdio Transport | ✅ | ✅ | ✅ |
| HTTP Transport | ✅ | ✅ | ✅ |
| OAuth (built-in) | ✅ | ✅ | ❌ |
| Enterprise Auth | ❌ | ✅ | ❌ |
| Server Composition | ❌ | ✅ | ❌ |
| Proxy Servers | ❌ | ✅ | ❌ |
| OpenAPI Generation | ❌ | ✅ | ❌ |
| FastAPI Integration | ❌ | ✅ | ❌ |
| MCP Inspector | ✅ | ✅ | ✅ |

## Recommendations

**Choose Python SDK when:**
- Building standard MCP servers
- Contributing to official SDK
- Need minimal dependencies

**Choose FastMCP when:**
- Building production applications
- Need enterprise authentication (Google, Azure, Auth0, etc.)
- Composing multiple MCP servers
- Proxying or transforming existing servers
- Generating MCP from OpenAPI/FastAPI

**Choose TypeScript SDK when:**
- Building Node.js applications
- Using TypeScript for type safety
- Integrating with npm ecosystem
- Building browser-compatible clients
