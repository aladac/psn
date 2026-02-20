#!/usr/bin/env python3
"""Indexer MCP Server.

Provides code and document indexing with semantic search.
Uses Ollama for embeddings and PostgreSQL/pgvector for storage.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

import psycopg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pgvector.psycopg import register_vector

from personality.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("indexer")

# File extensions to index
CODE_EXTENSIONS = {".py", ".rs", ".rb", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".h"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}


def get_connection() -> psycopg.Connection:
    """Get a PostgreSQL connection."""
    cfg = get_config().postgres
    conn = psycopg.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.database,
        user=cfg.user,
    )
    register_vector(conn)
    return conn


def get_embedding(text: str) -> list[float]:
    """Get embedding for text using Ollama API."""
    cfg = get_config().ollama
    # Truncate to avoid token limits
    truncated = text[:8000]

    url = f"{cfg.url}/api/embeddings"
    data = json.dumps({"model": cfg.embedding_model, "prompt": truncated}).encode()

    try:
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["embedding"]
    except URLError as e:
        logger.error(f"Ollama embedding failed: {e}")
        raise
    except KeyError:
        logger.error(f"Unexpected Ollama response: {result}")
        raise


def ensure_schema(conn: psycopg.Connection) -> None:
    """Ensure the index tables exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS code_index (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                language TEXT,
                project TEXT,
                indexed_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doc_index (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                project TEXT,
                indexed_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS code_embedding_idx
            ON code_index USING ivfflat (embedding vector_cosine_ops)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS doc_embedding_idx
            ON doc_index USING ivfflat (embedding vector_cosine_ops)
        """)
    conn.commit()


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

    try:
        with get_connection() as conn:
            ensure_schema(conn)

            if name == "index_code":
                result = index_code(conn, arguments)
            elif name == "index_docs":
                result = index_docs(conn, arguments)
            elif name == "search":
                result = search_index(conn, arguments)
            elif name == "status":
                result = get_status(conn, arguments)
            elif name == "clear":
                result = clear_index(conn, arguments)
            else:
                result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.exception(f"Error in tool {name}")
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def index_code(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Index code files in a directory."""
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

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO code_index (id, path, content, embedding, language, project)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            indexed_at = NOW()
                        """,
                        (chunk_id, str(file_path), chunk, embedding, file_path.suffix, project),
                    )
                conn.commit()
                indexed += 1

        except Exception as e:
            errors.append(f"{file_path}: {e}")

    return {"success": True, "indexed": indexed, "project": project, "errors": errors[:5]}


def index_docs(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Index documentation files in a directory."""
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

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO doc_index (id, path, content, embedding, project)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            indexed_at = NOW()
                        """,
                        (chunk_id, str(file_path), chunk, embedding, project),
                    )
                conn.commit()
                indexed += 1

        except Exception as e:
            errors.append(f"{file_path}: {e}")

    return {"success": True, "indexed": indexed, "project": project, "errors": errors[:5]}


def search_index(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search indexed code and docs."""
    query = arguments["query"]
    search_type = arguments.get("type", "all")
    limit = arguments.get("limit", 10)
    project_filter = arguments.get("project")

    embedding = get_embedding(query)
    results = []

    with conn.cursor() as cur:
        if search_type in ("code", "all"):
            if project_filter:
                cur.execute(
                    """
                    SELECT path, content, 1 - (embedding <=> %s::vector) AS similarity
                    FROM code_index
                    WHERE project = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, project_filter, embedding, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT path, content, 1 - (embedding <=> %s::vector) AS similarity
                    FROM code_index
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, embedding, limit),
                )

            for row in cur.fetchall():
                results.append({
                    "type": "code",
                    "path": row[0],
                    "content": row[1][:500],  # Truncate for readability
                    "similarity": float(row[2]),
                })

        if search_type in ("docs", "all"):
            if project_filter:
                cur.execute(
                    """
                    SELECT path, content, 1 - (embedding <=> %s::vector) AS similarity
                    FROM doc_index
                    WHERE project = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, project_filter, embedding, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT path, content, 1 - (embedding <=> %s::vector) AS similarity
                    FROM doc_index
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, embedding, limit),
                )

            for row in cur.fetchall():
                results.append({
                    "type": "docs",
                    "path": row[0],
                    "content": row[1][:500],
                    "similarity": float(row[2]),
                })

    # Sort combined results by similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return {"success": True, "results": results[:limit]}


def get_status(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get indexing status and statistics."""
    project_filter = arguments.get("project")

    with conn.cursor() as cur:
        if project_filter:
            cur.execute(
                "SELECT project, COUNT(*) FROM code_index WHERE project = %s GROUP BY project",
                (project_filter,),
            )
        else:
            cur.execute("SELECT project, COUNT(*) FROM code_index GROUP BY project")
        code_stats = [{"project": row[0], "count": row[1]} for row in cur.fetchall()]

        if project_filter:
            cur.execute(
                "SELECT project, COUNT(*) FROM doc_index WHERE project = %s GROUP BY project",
                (project_filter,),
            )
        else:
            cur.execute("SELECT project, COUNT(*) FROM doc_index GROUP BY project")
        doc_stats = [{"project": row[0], "count": row[1]} for row in cur.fetchall()]

    return {"success": True, "code_index": code_stats, "doc_index": doc_stats}


def clear_index(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Clear index for a project or all."""
    clear_type = arguments.get("type", "all")
    project_filter = arguments.get("project")

    with conn.cursor() as cur:
        if clear_type in ("code", "all"):
            if project_filter:
                cur.execute("DELETE FROM code_index WHERE project = %s", (project_filter,))
            else:
                cur.execute("DELETE FROM code_index")

        if clear_type in ("docs", "all"):
            if project_filter:
                cur.execute("DELETE FROM doc_index WHERE project = %s", (project_filter,))
            else:
                cur.execute("DELETE FROM doc_index")

    conn.commit()
    return {"success": True, "cleared": clear_type, "project": project_filter or "all"}


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
