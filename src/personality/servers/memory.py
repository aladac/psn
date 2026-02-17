#!/usr/bin/env python3
"""Memory MCP Server.

Provides persistent memory via embeddings and vector search.
Uses Ollama for embeddings and PostgreSQL/pgvector for storage.
"""
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Any
from uuid import uuid4

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("memory")

JUNKPILE_HOST = os.environ.get("JUNKPILE_HOST", "junkpile")
SSH_KEY = os.environ.get("SSH_KEY", "/Users/chi/.ssh/id_ed25519")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
PG_DATABASE = os.environ.get("PG_DATABASE", "personality")
PG_LOCAL = os.environ.get("PG_LOCAL", "false").lower() == "true"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "")  # Empty = use junkpile via SSH


def ssh_command(cmd: str) -> dict[str, Any]:
    """Run a command on junkpile via SSH."""
    ssh_cmd = ["ssh", "-i", SSH_KEY, JUNKPILE_HOST, cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=120)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_embedding(text: str) -> list[float] | None:
    """Get embedding for text via Ollama."""
    data = json.dumps({"model": EMBEDDING_MODEL, "input": text})

    if OLLAMA_HOST:
        # Local or direct Ollama connection
        import urllib.request
        import urllib.error

        url = f"http://{OLLAMA_HOST}/api/embed"
        req = urllib.request.Request(url, data=data.encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response = json.loads(resp.read().decode())
                return response.get("embedding")
        except (urllib.error.URLError, json.JSONDecodeError):
            return None
    else:
        # Via SSH to junkpile
        cmd = f"curl -s -X POST http://localhost:11434/api/embed -d '{data}'"
        result = ssh_command(cmd)
        if result.get("success") and result.get("stdout"):
            try:
                response = json.loads(result["stdout"])
                return response.get("embedding")
            except json.JSONDecodeError:
                pass
        return None


def run_psql(query: str) -> dict[str, Any]:
    """Execute a PostgreSQL query locally or on junkpile."""
    escaped_query = query.replace("'", "'\"'\"'")
    cmd = f"psql -d {PG_DATABASE} -t -A -c '{escaped_query}'"

    if PG_LOCAL:
        # Run locally
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        return ssh_command(cmd)


def ensure_schema() -> None:
    """Ensure the memories table exists."""
    schema_sql = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS memories (
        id UUID PRIMARY KEY,
        subject TEXT NOT NULL,
        content TEXT NOT NULL,
        embedding vector(768),
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS memories_subject_idx ON memories (subject);
    """
    run_psql(schema_sql)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available memory tools."""
    return [
        Tool(
            name="store",
            description="Store a memory with subject and content. Automatically generates embedding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Memory subject/category"},
                    "content": {"type": "string", "description": "Memory content to store"},
                    "metadata": {"type": "object", "description": "Additional metadata"},
                },
                "required": ["subject", "content"],
            },
        ),
        Tool(
            name="recall",
            description="Recall memories by semantic similarity to a query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query to search for"},
                    "limit": {"type": "integer", "description": "Max results (default: 5)"},
                    "subject": {"type": "string", "description": "Filter by subject"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search",
            description="Search memories by subject or metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subject to search"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
            },
        ),
        Tool(
            name="forget",
            description="Delete a memory by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Memory UUID to delete"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="list",
            description="List all memory subjects and counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with {arguments}")

    # Ensure schema exists
    ensure_schema()

    if name == "store":
        memory_id = str(uuid4())
        subject = arguments["subject"]
        content = arguments["content"]
        metadata = json.dumps(arguments.get("metadata", {}))

        # Get embedding
        embedding = get_embedding(content)
        if not embedding:
            result = {"success": False, "error": "Failed to generate embedding"}
        else:
            vec_str = "[" + ",".join(map(str, embedding)) + "]"
            sql = f"""
                INSERT INTO memories (id, subject, content, embedding, metadata)
                VALUES ('{memory_id}', '{subject}', '{content.replace("'", "''")}', '{vec_str}', '{metadata}')
            """
            db_result = run_psql(sql)
            if db_result.get("success"):
                result = {"success": True, "id": memory_id, "subject": subject}
            else:
                result = {"success": False, "error": db_result.get("stderr", "Unknown error")}

    elif name == "recall":
        query = arguments["query"]
        limit = arguments.get("limit", 5)

        embedding = get_embedding(query)
        if not embedding:
            result = {"success": False, "error": "Failed to generate query embedding"}
        else:
            vec_str = "[" + ",".join(map(str, embedding)) + "]"
            sql = f"""
                SELECT id, subject, content, metadata,
                       1 - (embedding <=> '{vec_str}') AS similarity
                FROM memories
            """
            if arguments.get("subject"):
                sql += f" WHERE subject = '{arguments['subject']}'"
            sql += f" ORDER BY embedding <=> '{vec_str}' LIMIT {limit}"

            db_result = run_psql(sql)
            if db_result.get("success"):
                result = {"success": True, "memories": db_result.get("stdout", "").strip().split("\n")}
            else:
                result = {"success": False, "error": db_result.get("stderr")}

    elif name == "search":
        sql = "SELECT id, subject, content, created_at FROM memories"
        if arguments.get("subject"):
            sql += f" WHERE subject LIKE '%{arguments['subject']}%'"
        sql += f" ORDER BY created_at DESC LIMIT {arguments.get('limit', 20)}"

        db_result = run_psql(sql)
        result = {
            "success": db_result.get("success", False),
            "memories": db_result.get("stdout", "").strip().split("\n") if db_result.get("success") else [],
        }

    elif name == "forget":
        sql = f"DELETE FROM memories WHERE id = '{arguments['id']}'"
        db_result = run_psql(sql)
        result = {"success": db_result.get("success", False), "deleted": arguments["id"]}

    elif name == "list":
        sql = "SELECT subject, COUNT(*) as count FROM memories GROUP BY subject ORDER BY count DESC"
        db_result = run_psql(sql)
        result = {
            "success": db_result.get("success", False),
            "subjects": db_result.get("stdout", "").strip().split("\n") if db_result.get("success") else [],
        }

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
