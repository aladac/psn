#!/usr/bin/env python3
"""Ollama MCP Server.

Provides embedding and generation capabilities via Ollama on junkpile.
"""
import json
import logging
import os
import subprocess
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("ollama")

JUNKPILE_HOST = os.environ.get("JUNKPILE_HOST", "junkpile")
SSH_KEY = os.environ.get("SSH_KEY", "/Users/chi/.ssh/id_ed25519")
OLLAMA_PORT = 11434


def run_ollama_api(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call Ollama API on junkpile via SSH tunnel."""
    if data:
        curl_cmd = f"curl -s -X POST http://localhost:{OLLAMA_PORT}{endpoint} -d '{json.dumps(data)}'"
    else:
        curl_cmd = f"curl -s http://localhost:{OLLAMA_PORT}{endpoint}"

    ssh_cmd = ["ssh", "-i", SSH_KEY, JUNKPILE_HOST, curl_cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return {"success": True, "data": json.loads(result.stdout) if result.stdout else {}}
        return {"success": False, "error": result.stderr}
    except json.JSONDecodeError:
        return {"success": True, "data": result.stdout}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Ollama tools."""
    return [
        Tool(
            name="embed",
            description="Generate embeddings for text using nomic-embed-text or other model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to embed"},
                    "model": {
                        "type": "string",
                        "description": "Embedding model (default: nomic-embed-text)",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="generate",
            description="Generate text using a language model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Prompt for generation"},
                    "model": {"type": "string", "description": "Model to use"},
                    "stream": {"type": "boolean", "description": "Stream response"},
                },
                "required": ["prompt", "model"],
            },
        ),
        Tool(
            name="models",
            description="List available models on Ollama.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="pull",
            description="Pull/download a model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name to pull"},
                },
                "required": ["model"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with {arguments}")

    if name == "embed":
        model = arguments.get("model", "nomic-embed-text")
        result = run_ollama_api("/api/embeddings", {"model": model, "prompt": arguments["text"]})

    elif name == "generate":
        result = run_ollama_api(
            "/api/generate",
            {
                "model": arguments["model"],
                "prompt": arguments["prompt"],
                "stream": arguments.get("stream", False),
            },
        )

    elif name == "models":
        result = run_ollama_api("/api/tags")

    elif name == "pull":
        result = run_ollama_api("/api/pull", {"name": arguments["model"]})

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
