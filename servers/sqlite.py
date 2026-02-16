#!/usr/bin/env python3
"""SQLite MCP Server.

Provides local database access with vector search via sqlite-vec.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("sqlite")

# Default database location
DEFAULT_DB = Path.home() / ".local" / "share" / "personality" / "local.db"


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection, creating directory if needed."""
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    # Try to load sqlite-vec extension
    try:
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        logger.info("sqlite-vec extension loaded")
    except Exception as e:
        logger.warning(f"sqlite-vec not available: {e}")

    return conn


def execute_query(sql: str, db_path: str | None = None, params: tuple = ()) -> dict[str, Any]:
    """Execute a SQL query and return results."""
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(sql, params)

        if sql.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            result = {
                "success": True,
                "columns": columns,
                "rows": [dict(row) for row in rows],
                "count": len(rows),
            }
        else:
            conn.commit()
            result = {
                "success": True,
                "rowcount": cursor.rowcount,
                "lastrowid": cursor.lastrowid,
            }

        conn.close()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available SQLite tools."""
    return [
        Tool(
            name="query",
            description="Execute a SELECT query and return results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL SELECT query"},
                    "database": {"type": "string", "description": "Database file path"},
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="execute",
            description="Execute a modifying SQL statement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL statement"},
                    "database": {"type": "string", "description": "Database file path"},
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="vector_search",
            description="Search for similar vectors using sqlite-vec.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Virtual table name"},
                    "embedding": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Query embedding vector",
                    },
                    "limit": {"type": "integer", "description": "Number of results"},
                    "database": {"type": "string", "description": "Database file path"},
                },
                "required": ["table", "embedding"],
            },
        ),
        Tool(
            name="attach",
            description="Attach another database file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to database file"},
                    "alias": {"type": "string", "description": "Alias for attached database"},
                    "database": {"type": "string", "description": "Main database file path"},
                },
                "required": ["path", "alias"],
            },
        ),
        Tool(
            name="tables",
            description="List tables in the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": "Database file path"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with {arguments}")

    if name == "query":
        result = execute_query(arguments["sql"], arguments.get("database"))

    elif name == "execute":
        result = execute_query(arguments["sql"], arguments.get("database"))

    elif name == "vector_search":
        table = arguments["table"]
        embedding = arguments["embedding"]
        limit = arguments.get("limit", 10)

        # sqlite-vec uses vec_distance_L2 or similar
        vec_blob = json.dumps(embedding)
        sql = f"""
            SELECT rowid, distance
            FROM {table}
            WHERE embedding MATCH '{vec_blob}'
            ORDER BY distance
            LIMIT {limit}
        """
        result = execute_query(sql, arguments.get("database"))

    elif name == "attach":
        sql = f"ATTACH DATABASE '{arguments['path']}' AS {arguments['alias']}"
        result = execute_query(sql, arguments.get("database"))

    elif name == "tables":
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = execute_query(sql, arguments.get("database"))

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
