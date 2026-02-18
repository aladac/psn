#!/usr/bin/env python3
"""PostgreSQL MCP Server.

Provides database access and vector search via pgvector.
Uses psycopg for direct PostgreSQL connections.
"""
import json
import logging
from typing import Any

import psycopg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pgvector.psycopg import register_vector

from personality.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("postgres")


def get_connection(database: str | None = None) -> psycopg.Connection:
    """Get a PostgreSQL connection."""
    cfg = get_config().postgres
    conn = psycopg.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=database or cfg.database,
        user=cfg.user,
    )
    register_vector(conn)
    return conn


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

    try:
        with get_connection(arguments.get("database")) as conn:
            if name == "query":
                result = execute_query(conn, arguments["sql"])
            elif name == "execute":
                result = execute_statement(conn, arguments["sql"])
            elif name == "vector_search":
                result = vector_search(conn, arguments)
            elif name == "schema":
                result = get_schema(conn, arguments.get("table"))
            else:
                result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.exception(f"Error in tool {name}")
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def execute_query(conn: psycopg.Connection, sql: str) -> dict[str, Any]:
    """Execute a SELECT query and return results."""
    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()

        # Convert rows to list of dicts
        results = []
        for row in rows:
            results.append(dict(zip(columns, [serialize_value(v) for v in row])))

    return {"success": True, "columns": columns, "rows": results, "count": len(results)}


def execute_statement(conn: psycopg.Connection, sql: str) -> dict[str, Any]:
    """Execute a modifying SQL statement."""
    with conn.cursor() as cur:
        cur.execute(sql)
        rowcount = cur.rowcount
    conn.commit()

    return {"success": True, "affected_rows": rowcount}


def vector_search(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search for similar vectors using pgvector."""
    table = arguments["table"]
    column = arguments["column"]
    embedding = arguments["embedding"]
    limit = arguments.get("limit", 10)
    threshold = arguments.get("threshold")

    with conn.cursor() as cur:
        if threshold:
            cur.execute(
                f"""
                SELECT *, {column} <-> %s::vector AS distance
                FROM {table}
                WHERE {column} <-> %s::vector < %s
                ORDER BY {column} <-> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, threshold, embedding, limit),
            )
        else:
            cur.execute(
                f"""
                SELECT *, {column} <-> %s::vector AS distance
                FROM {table}
                ORDER BY {column} <-> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, limit),
            )

        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()

        results = []
        for row in rows:
            results.append(dict(zip(columns, [serialize_value(v) for v in row])))

    return {"success": True, "columns": columns, "rows": results, "count": len(results)}


def get_schema(conn: psycopg.Connection, table: str | None = None) -> dict[str, Any]:
    """Get database schema information."""
    with conn.cursor() as cur:
        if table:
            # Get column info for specific table
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (table,),
            )
            columns = cur.fetchall()
            schema = [
                {
                    "column": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[3],
                }
                for col in columns
            ]
            return {"success": True, "table": table, "columns": schema}
        else:
            # List all tables
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cur.fetchall()]
            return {"success": True, "tables": tables}


def serialize_value(value: Any) -> Any:
    """Serialize a value for JSON output."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    # Handle datetime, UUID, etc.
    return str(value)


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
