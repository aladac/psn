#!/usr/bin/env python3
"""Ollama MCP Server.

Provides embedding and generation capabilities via Ollama.
Uses httpx for HTTP communication.
"""
import json
import logging
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from personality.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("ollama")


def get_client() -> httpx.Client:
    """Get an httpx client configured for Ollama."""
    cfg = get_config().ollama
    return httpx.Client(base_url=cfg.url, timeout=300.0)


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

    try:
        with get_client() as client:
            if name == "embed":
                model = arguments.get("model", "nomic-embed-text")
                response = client.post(
                    "/api/embed",
                    json={"model": model, "input": arguments["text"]},
                )
                response.raise_for_status()
                result = {"success": True, "data": response.json()}

            elif name == "generate":
                response = client.post(
                    "/api/generate",
                    json={
                        "model": arguments["model"],
                        "prompt": arguments["prompt"],
                        "stream": arguments.get("stream", False),
                    },
                )
                response.raise_for_status()
                result = {"success": True, "data": response.json()}

            elif name == "models":
                response = client.get("/api/tags")
                response.raise_for_status()
                result = {"success": True, "data": response.json()}

            elif name == "pull":
                response = client.post(
                    "/api/pull",
                    json={"name": arguments["model"]},
                )
                response.raise_for_status()
                result = {"success": True, "data": response.json()}

            else:
                result = {"error": f"Unknown tool: {name}"}

    except httpx.HTTPStatusError as e:
        result = {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        result = {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
