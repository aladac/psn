#!/usr/bin/env python3
"""PostgreSQL MCP Server.

Provides database access and vector search via pgvector on junkpile.
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

server = Server("postgres")

JUNKPILE_HOST = os.environ.get("JUNKPILE_HOST", "junkpile")
SSH_KEY = os.environ.get("SSH_KEY", "/Users/chi/.ssh/id_ed25519")
PG_DATABASE = os.environ.get("PG_DATABASE", "personality")
PG_LOCAL = os.environ.get("PG_LOCAL", "false").lower() == "true"


def run_psql(query: str, database: str | None = None) -> dict[str, Any]:
    """Execute a PostgreSQL query locally or on junkpile via SSH."""
    db = database or PG_DATABASE
    escaped_query = query.replace('"', '\\"').replace("'", "'\\''")

    if PG_LOCAL:
        # Run locally
        psql_cmd = f'psql -d {db} -t -A -c "{escaped_query}"'
        try:
            result = subprocess.run(psql_cmd, shell=True, capture_output=True, text=True, timeout=60)
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Query timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        # Via SSH to junkpile
        psql_cmd = f"sudo -u postgres psql -d {db} -t -A -c \"{escaped_query}\""
        ssh_cmd = ["ssh", "-i", SSH_KEY, JUNKPILE_HOST, psql_cmd]
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Query timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available PostgreSQL tools."""
    return [
        Tool(
            name="query",
            description="Execute a SELECT query and return results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL SELECT query"},
                    "database": {"type": "string", "description": "Database name (default: personality)"},
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="execute",
            description="Execute a modifying SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL statement"},
                    "database": {"type": "string", "description": "Database name"},
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="vector_search",
            description="Search for similar vectors using pgvector.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table with vector column"},
                    "column": {"type": "string", "description": "Vector column name"},
                    "embedding": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Query embedding vector",
                    },
                    "limit": {"type": "integer", "description": "Number of results (default: 10)"},
                    "threshold": {"type": "number", "description": "Distance threshold"},
                },
                "required": ["table", "column", "embedding"],
            },
        ),
        Tool(
            name="schema",
            description="Get database schema information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name (optional, lists all if omitted)"},
                    "database": {"type": "string", "description": "Database name"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with {arguments}")

    if name == "query":
        result = run_psql(arguments["sql"], arguments.get("database"))

    elif name == "execute":
        result = run_psql(arguments["sql"], arguments.get("database"))

    elif name == "vector_search":
        table = arguments["table"]
        column = arguments["column"]
        embedding = arguments["embedding"]
        limit = arguments.get("limit", 10)

        # Format embedding as PostgreSQL array
        vec_str = "[" + ",".join(map(str, embedding)) + "]"
        query = f"""
            SELECT *, {column} <-> '{vec_str}' AS distance
            FROM {table}
            ORDER BY {column} <-> '{vec_str}'
            LIMIT {limit}
        """
        if arguments.get("threshold"):
            query = f"""
                SELECT *, {column} <-> '{vec_str}' AS distance
                FROM {table}
                WHERE {column} <-> '{vec_str}' < {arguments['threshold']}
                ORDER BY {column} <-> '{vec_str}'
                LIMIT {limit}
            """
        result = run_psql(query, arguments.get("database"))

    elif name == "schema":
        if arguments.get("table"):
            query = f"\\d {arguments['table']}"
        else:
            query = "\\dt"
        result = run_psql(query, arguments.get("database"))

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
