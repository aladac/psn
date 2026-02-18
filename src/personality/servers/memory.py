#!/usr/bin/env python3
"""Memory MCP Server.

Provides persistent memory via embeddings and vector search.
Uses sentence-transformers for embeddings and PostgreSQL/pgvector for storage.
"""
import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from personality.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("memory")

# Lazy-loaded model
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Get or initialize the embedding model."""
    global _model
    if _model is None:
        cfg = get_config().ollama
        logger.info(f"Loading embedding model: {cfg.embedding_model}")
        _model = SentenceTransformer(cfg.embedding_model, trust_remote_code=True)
        logger.info("Model loaded successfully")
    return _model


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
    """Get embedding for text using sentence-transformers."""
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def ensure_schema(conn: psycopg.Connection) -> None:
    """Ensure the memories table exists."""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS memories_embedding_idx
            ON memories USING ivfflat (embedding vector_cosine_ops)
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS memories_subject_idx ON memories (subject)")
    conn.commit()


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

    try:
        with get_connection() as conn:
            ensure_schema(conn)

            if name == "store":
                result = store_memory(conn, arguments)
            elif name == "recall":
                result = recall_memories(conn, arguments)
            elif name == "search":
                result = search_memories(conn, arguments)
            elif name == "forget":
                result = forget_memory(conn, arguments)
            elif name == "list":
                result = list_subjects(conn)
            else:
                result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.exception(f"Error in tool {name}")
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def store_memory(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Store a new memory."""
    memory_id = str(uuid4())
    subject = arguments["subject"]
    content = arguments["content"]
    metadata = arguments.get("metadata", {})

    embedding = get_embedding(content)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO memories (id, subject, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (memory_id, subject, content, embedding, json.dumps(metadata)),
        )
    conn.commit()

    return {"success": True, "id": memory_id, "subject": subject}


def recall_memories(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Recall memories by semantic similarity."""
    query = arguments["query"]
    limit = arguments.get("limit", 5)
    subject_filter = arguments.get("subject")

    embedding = get_embedding(query)

    with conn.cursor() as cur:
        if subject_filter:
            cur.execute(
                """
                SELECT id, subject, content, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM memories
                WHERE subject = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, subject_filter, embedding, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, subject, content, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM memories
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, limit),
            )

        rows = cur.fetchall()
        memories = [
            {
                "id": str(row[0]),
                "subject": row[1],
                "content": row[2],
                "metadata": row[3],
                "similarity": float(row[4]),
            }
            for row in rows
        ]

    return {"success": True, "memories": memories}


def search_memories(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search memories by subject."""
    subject_filter = arguments.get("subject")
    limit = arguments.get("limit", 20)

    with conn.cursor() as cur:
        if subject_filter:
            cur.execute(
                """
                SELECT id, subject, content, created_at
                FROM memories
                WHERE subject LIKE %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (f"%{subject_filter}%", limit),
            )
        else:
            cur.execute(
                """
                SELECT id, subject, content, created_at
                FROM memories
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

        rows = cur.fetchall()
        memories = [
            {
                "id": str(row[0]),
                "subject": row[1],
                "content": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in rows
        ]

    return {"success": True, "memories": memories}


def forget_memory(conn: psycopg.Connection, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a memory by ID."""
    memory_id = arguments["id"]

    with conn.cursor() as cur:
        cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
        deleted = cur.rowcount > 0
    conn.commit()

    return {"success": deleted, "deleted": memory_id if deleted else None}


def list_subjects(conn: psycopg.Connection) -> dict[str, Any]:
    """List all memory subjects with counts."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT subject, COUNT(*) as count
            FROM memories
            GROUP BY subject
            ORDER BY count DESC
            """
        )
        rows = cur.fetchall()
        subjects = [f"{row[0]}|{row[1]}" for row in rows]

    return {"success": True, "subjects": subjects}


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
