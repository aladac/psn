#!/usr/bin/env python3
"""Indexer MCP Server.

Provides code and document indexing with semantic search.
"""
import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("indexer")

JUNKPILE_HOST = os.environ.get("JUNKPILE_HOST", "junkpile")
SSH_KEY = os.environ.get("SSH_KEY", "/Users/chi/.ssh/id_ed25519")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
PG_DATABASE = "personality"

# File extensions to index
CODE_EXTENSIONS = {".py", ".rs", ".rb", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".h"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}


def ssh_command(cmd: str) -> dict[str, Any]:
    """Run a command on junkpile via SSH."""
    ssh_cmd = ["ssh", "-i", SSH_KEY, JUNKPILE_HOST, cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_embedding(text: str) -> list[float] | None:
    """Get embedding for text via Ollama on junkpile."""
    data = json.dumps({"model": EMBEDDING_MODEL, "prompt": text[:8000]})  # Truncate long text
    cmd = f"curl -s -X POST http://localhost:11434/api/embeddings -d '{data}'"
    result = ssh_command(cmd)

    if result.get("success") and result.get("stdout"):
        try:
            response = json.loads(result["stdout"])
            return response.get("embedding")
        except json.JSONDecodeError:
            pass
    return None


def run_psql(query: str) -> dict[str, Any]:
    """Execute a PostgreSQL query on junkpile."""
    escaped_query = query.replace("'", "'\"'\"'")
    cmd = f"psql -d {PG_DATABASE} -t -A -c '{escaped_query}'"
    return ssh_command(cmd)


def ensure_schema() -> None:
    """Ensure the index tables exist."""
    schema_sql = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS code_index (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        content TEXT NOT NULL,
        embedding vector(768),
        language TEXT,
        project TEXT,
        indexed_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS doc_index (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        content TEXT NOT NULL,
        embedding vector(768),
        project TEXT,
        indexed_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS code_embedding_idx ON code_index USING ivfflat (embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS doc_embedding_idx ON doc_index USING ivfflat (embedding vector_cosine_ops);
    """
    run_psql(schema_sql)


def chunk_content(content: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Split content into overlapping chunks."""
    if len(content) <= chunk_size:
        return [content]

    chunks = []
    start = 0
    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available indexer tools."""
    return [
        Tool(
            name="index_code",
            description="Index code files in a directory for semantic search.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to index"},
                    "project": {"type": "string", "description": "Project name for grouping"},
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to include",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="index_docs",
            description="Index documentation files for semantic search.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to index"},
                    "project": {"type": "string", "description": "Project name"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="search",
            description="Search indexed code and docs by semantic similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "type": {
                        "type": "string",
                        "enum": ["code", "docs", "all"],
                        "description": "What to search",
                    },
                    "project": {"type": "string", "description": "Filter by project"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="status",
            description="Show indexing status and statistics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Filter by project"},
                },
            },
        ),
        Tool(
            name="clear",
            description="Clear index for a project or all.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project to clear (omit for all)"},
                    "type": {"type": "string", "enum": ["code", "docs", "all"], "description": "What to clear"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with {arguments}")

    ensure_schema()

    if name == "index_code":
        path = Path(arguments["path"]).expanduser()
        project = arguments.get("project", path.name)
        extensions = set(arguments.get("extensions", CODE_EXTENSIONS))

        indexed = 0
        errors = []

        for file_path in path.rglob("*"):
            if file_path.suffix not in extensions or not file_path.is_file():
                continue

            try:
                content = file_path.read_text(errors="ignore")
                if len(content) < 10:
                    continue

                for i, chunk in enumerate(chunk_content(content)):
                    chunk_id = hashlib.md5(f"{file_path}:{i}".encode()).hexdigest()
                    embedding = get_embedding(chunk)

                    if embedding:
                        vec_str = "[" + ",".join(map(str, embedding)) + "]"
                        sql = f"""
                            INSERT INTO code_index (id, path, content, embedding, language, project)
                            VALUES ('{chunk_id}', '{str(file_path)}', '{chunk.replace("'", "''")}',
                                    '{vec_str}', '{file_path.suffix}', '{project}')
                            ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                        """
                        run_psql(sql)
                        indexed += 1

            except Exception as e:
                errors.append(f"{file_path}: {e}")

        result = {"success": True, "indexed": indexed, "project": project, "errors": errors[:5]}

    elif name == "index_docs":
        path = Path(arguments["path"]).expanduser()
        project = arguments.get("project", path.name)

        indexed = 0
        errors = []

        for file_path in path.rglob("*"):
            if file_path.suffix not in DOC_EXTENSIONS or not file_path.is_file():
                continue

            try:
                content = file_path.read_text(errors="ignore")
                if len(content) < 10:
                    continue

                for i, chunk in enumerate(chunk_content(content)):
                    chunk_id = hashlib.md5(f"{file_path}:{i}".encode()).hexdigest()
                    embedding = get_embedding(chunk)

                    if embedding:
                        vec_str = "[" + ",".join(map(str, embedding)) + "]"
                        sql = f"""
                            INSERT INTO doc_index (id, path, content, embedding, project)
                            VALUES ('{chunk_id}', '{str(file_path)}', '{chunk.replace("'", "''")}',
                                    '{vec_str}', '{project}')
                            ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                        """
                        run_psql(sql)
                        indexed += 1

            except Exception as e:
                errors.append(f"{file_path}: {e}")

        result = {"success": True, "indexed": indexed, "project": project, "errors": errors[:5]}

    elif name == "search":
        query = arguments["query"]
        search_type = arguments.get("type", "all")
        limit = arguments.get("limit", 10)

        embedding = get_embedding(query)
        if not embedding:
            result = {"success": False, "error": "Failed to generate query embedding"}
        else:
            vec_str = "[" + ",".join(map(str, embedding)) + "]"
            results = []

            if search_type in ("code", "all"):
                sql = f"""
                    SELECT path, content, 1 - (embedding <=> '{vec_str}') AS similarity
                    FROM code_index
                """
                if arguments.get("project"):
                    sql += f" WHERE project = '{arguments['project']}'"
                sql += f" ORDER BY embedding <=> '{vec_str}' LIMIT {limit}"
                db_result = run_psql(sql)
                if db_result.get("success"):
                    results.extend([{"type": "code", "line": l} for l in db_result.get("stdout", "").strip().split("\n") if l])

            if search_type in ("docs", "all"):
                sql = f"""
                    SELECT path, content, 1 - (embedding <=> '{vec_str}') AS similarity
                    FROM doc_index
                """
                if arguments.get("project"):
                    sql += f" WHERE project = '{arguments['project']}'"
                sql += f" ORDER BY embedding <=> '{vec_str}' LIMIT {limit}"
                db_result = run_psql(sql)
                if db_result.get("success"):
                    results.extend([{"type": "docs", "line": l} for l in db_result.get("stdout", "").strip().split("\n") if l])

            result = {"success": True, "results": results}

    elif name == "status":
        code_sql = "SELECT project, COUNT(*) FROM code_index GROUP BY project"
        doc_sql = "SELECT project, COUNT(*) FROM doc_index GROUP BY project"

        if arguments.get("project"):
            code_sql = f"SELECT project, COUNT(*) FROM code_index WHERE project = '{arguments['project']}' GROUP BY project"
            doc_sql = f"SELECT project, COUNT(*) FROM doc_index WHERE project = '{arguments['project']}' GROUP BY project"

        code_result = run_psql(code_sql)
        doc_result = run_psql(doc_sql)

        result = {
            "success": True,
            "code_index": code_result.get("stdout", "").strip().split("\n") if code_result.get("success") else [],
            "doc_index": doc_result.get("stdout", "").strip().split("\n") if doc_result.get("success") else [],
        }

    elif name == "clear":
        clear_type = arguments.get("type", "all")

        if clear_type in ("code", "all"):
            sql = "DELETE FROM code_index"
            if arguments.get("project"):
                sql += f" WHERE project = '{arguments['project']}'"
            run_psql(sql)

        if clear_type in ("docs", "all"):
            sql = "DELETE FROM doc_index"
            if arguments.get("project"):
                sql += f" WHERE project = '{arguments['project']}'"
            run_psql(sql)

        result = {"success": True, "cleared": clear_type, "project": arguments.get("project", "all")}

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
