#!/usr/bin/env python3
"""Docker Local MCP Server.

Manages Docker containers and images on the local machine (fuji/ARM).
"""
import json
import logging
import subprocess
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("docker-local")


def run_docker(*args: str) -> dict[str, Any]:
    """Run a docker command and return the result."""
    cmd = ["docker", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Docker tools."""
    return [
        Tool(
            name="containers",
            description="List running containers. Use all=true to include stopped.",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {"type": "boolean", "description": "Include stopped containers"},
                },
            },
        ),
        Tool(
            name="images",
            description="List Docker images.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="run",
            description="Run a new container.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image": {"type": "string", "description": "Image to run"},
                    "name": {"type": "string", "description": "Container name"},
                    "detach": {"type": "boolean", "description": "Run in background"},
                    "ports": {"type": "string", "description": "Port mapping (e.g., 8080:80)"},
                    "volumes": {"type": "string", "description": "Volume mapping"},
                    "env": {"type": "object", "description": "Environment variables"},
                    "command": {"type": "string", "description": "Command to run"},
                },
                "required": ["image"],
            },
        ),
        Tool(
            name="stop",
            description="Stop a running container.",
            inputSchema={
                "type": "object",
                "properties": {
                    "container": {"type": "string", "description": "Container name or ID"},
                },
                "required": ["container"],
            },
        ),
        Tool(
            name="logs",
            description="Get container logs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "container": {"type": "string", "description": "Container name or ID"},
                    "tail": {"type": "integer", "description": "Number of lines to show"},
                    "follow": {"type": "boolean", "description": "Follow log output"},
                },
                "required": ["container"],
            },
        ),
        Tool(
            name="exec",
            description="Execute a command in a running container.",
            inputSchema={
                "type": "object",
                "properties": {
                    "container": {"type": "string", "description": "Container name or ID"},
                    "command": {"type": "string", "description": "Command to execute"},
                },
                "required": ["container", "command"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with {arguments}")

    if name == "containers":
        args = ["ps", "--format", "json"]
        if arguments.get("all"):
            args.insert(1, "-a")
        result = run_docker(*args)

    elif name == "images":
        result = run_docker("images", "--format", "json")

    elif name == "run":
        args = ["run"]
        if arguments.get("detach"):
            args.append("-d")
        if arguments.get("name"):
            args.extend(["--name", arguments["name"]])
        if arguments.get("ports"):
            args.extend(["-p", arguments["ports"]])
        if arguments.get("volumes"):
            args.extend(["-v", arguments["volumes"]])
        if arguments.get("env"):
            for k, v in arguments["env"].items():
                args.extend(["-e", f"{k}={v}"])
        args.append(arguments["image"])
        if arguments.get("command"):
            args.extend(arguments["command"].split())
        result = run_docker(*args)

    elif name == "stop":
        result = run_docker("stop", arguments["container"])

    elif name == "logs":
        args = ["logs"]
        if arguments.get("tail"):
            args.extend(["--tail", str(arguments["tail"])])
        args.append(arguments["container"])
        result = run_docker(*args)

    elif name == "exec":
        result = run_docker("exec", arguments["container"], *arguments["command"].split())

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
