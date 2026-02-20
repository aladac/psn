#!/usr/bin/env python3
"""Memory MCP Server.

Provides persistent memory via embeddings and vector search.
Uses Ollama for embeddings and PostgreSQL/pgvector for storage.
Memories are scoped by cart (persona) for isolation between personas.
"""
import json
import logging
import os
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError
from uuid import uuid4

import psycopg
from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.stdio import stdio_server
from mcp.types import Resource, ResourceTemplate, TextContent, Tool
from pydantic import AnyUrl
from pgvector.psycopg import register_vector

from personality.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("memory")

# Default cart tag from environment or fallback
DEFAULT_CART_TAG = os.environ.get("PERSONALITY_CART", "default")


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
    url = f"{cfg.url}/api/embeddings"
    data = json.dumps({"model": cfg.embedding_model, "prompt": text}).encode()

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
    """Ensure the database schema exists."""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Carts table (persona registry)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tag TEXT UNIQUE NOT NULL,
                version TEXT,
                name TEXT,
                type TEXT,
                tagline TEXT,
                source TEXT,
                pcart_path TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS carts_tag_idx ON carts (tag)")

        # Memories table with cart_id foreign key
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY,
                cart_id UUID REFERENCES carts(id) ON DELETE CASCADE,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Migration: add cart_id column if missing (for existing tables)
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'memories' AND column_name = 'cart_id'
        """)
        if not cur.fetchone():
            logger.info("Migrating: adding cart_id column to memories table")
            cur.execute(
                "ALTER TABLE memories ADD COLUMN cart_id UUID REFERENCES carts(id) ON DELETE CASCADE"
            )

        cur.execute("""
            CREATE INDEX IF NOT EXISTS memories_embedding_idx
            ON memories USING ivfflat (embedding vector_cosine_ops)
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS memories_subject_idx ON memories (subject)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS memories_cart_id_idx ON memories (cart_id)"
        )
    conn.commit()


def get_or_create_cart(conn: psycopg.Connection, tag: str) -> str:
    """Get cart ID by tag, creating if not exists. Returns cart UUID."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM carts WHERE tag = %s", (tag,))
        row = cur.fetchone()
        if row:
            return str(row[0])

        # Create new cart
        cart_id = str(uuid4())
        cur.execute(
            "INSERT INTO carts (id, tag) VALUES (%s, %s)",
            (cart_id, tag),
        )
        conn.commit()
        logger.info(f"Created new cart: {tag} ({cart_id})")
        return cart_id


def get_active_cart_id(conn: psycopg.Connection) -> str:
    """Get the active cart ID, creating default if needed."""
    return get_or_create_cart(conn, DEFAULT_CART_TAG)


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
                    "subject": {
                        "type": "string",
                        "description": "Memory subject/category",
                    },
                    "content": {
                        "type": "string",
                        "description": "Memory content to store",
                    },
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
            cart_id = get_active_cart_id(conn)

            if name == "store":
                result = store_memory(conn, cart_id, arguments)
            elif name == "recall":
                result = recall_memories(conn, cart_id, arguments)
            elif name == "search":
                result = search_memories(conn, cart_id, arguments)
            elif name == "forget":
                result = forget_memory(conn, arguments)
            elif name == "list":
                result = list_subjects(conn, cart_id)
            else:
                result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.exception(f"Error in tool {name}")
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def store_memory(
    conn: psycopg.Connection, cart_id: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Store a new memory scoped to the active cart."""
    memory_id = str(uuid4())
    subject = arguments["subject"]
    content = arguments["content"]
    metadata = arguments.get("metadata", {})

    embedding = get_embedding(content)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO memories (id, cart_id, subject, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (memory_id, cart_id, subject, content, embedding, json.dumps(metadata)),
        )
    conn.commit()

    return {"success": True, "id": memory_id, "subject": subject}


def recall_memories(
    conn: psycopg.Connection, cart_id: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Recall memories by semantic similarity, scoped to active cart."""
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
                WHERE cart_id = %s AND subject = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, cart_id, subject_filter, embedding, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, subject, content, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM memories
                WHERE cart_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, cart_id, embedding, limit),
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


def search_memories(
    conn: psycopg.Connection, cart_id: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Search memories by subject, scoped to active cart."""
    subject_filter = arguments.get("subject")
    limit = arguments.get("limit", 20)

    with conn.cursor() as cur:
        if subject_filter:
            cur.execute(
                """
                SELECT id, subject, content, created_at
                FROM memories
                WHERE cart_id = %s AND subject LIKE %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (cart_id, f"%{subject_filter}%", limit),
            )
        else:
            cur.execute(
                """
                SELECT id, subject, content, created_at
                FROM memories
                WHERE cart_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (cart_id, limit),
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


def list_subjects(conn: psycopg.Connection, cart_id: str) -> dict[str, Any]:
    """List memory subjects with counts for the active cart."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT subject, COUNT(*) as count
            FROM memories
            WHERE cart_id = %s
            GROUP BY subject
            ORDER BY count DESC
            """,
            (cart_id,),
        )
        rows = cur.fetchall()
        subjects = [f"{row[0]}|{row[1]}" for row in rows]

    return {"success": True, "subjects": subjects}


# =============================================================================
# MCP Resources
# =============================================================================


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available memory resources."""
    return [
        Resource(
            uri=AnyUrl("memory://subjects"),
            name="Memory Subjects",
            description="List of all memory subjects with counts",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("memory://stats"),
            name="Memory Statistics",
            description="Overall memory statistics (total count, subjects, etc.)",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("memory://recent"),
            name="Recent Memories",
            description="Most recent 10 memories",
            mimeType="application/json",
        ),
    ]


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """List resource templates for dynamic resources."""
    return [
        ResourceTemplate(
            uriTemplate="memory://subject/{subject}",
            name="Memories by Subject",
            description="All memories for a specific subject",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
    """Read a memory resource by URI."""
    uri_str = str(uri)
    logger.info(f"Reading resource: {uri_str}")

    try:
        with get_connection() as conn:
            ensure_schema(conn)
            cart_id = get_active_cart_id(conn)

            if uri_str == "memory://subjects":
                result = _get_subjects_resource(conn, cart_id)
            elif uri_str == "memory://stats":
                result = _get_stats_resource(conn, cart_id)
            elif uri_str == "memory://recent":
                result = _get_recent_resource(conn, cart_id)
            elif uri_str.startswith("memory://subject/"):
                subject = uri_str.replace("memory://subject/", "")
                result = _get_subject_memories_resource(conn, cart_id, subject)
            else:
                result = {"error": f"Unknown resource: {uri_str}"}

    except Exception as e:
        logger.exception(f"Error reading resource {uri_str}")
        result = {"error": str(e)}

    return [ReadResourceContents(content=json.dumps(result, indent=2), mime_type="application/json")]


def _get_subjects_resource(conn: psycopg.Connection, cart_id: str) -> dict[str, Any]:
    """Get all subjects with counts."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT subject, COUNT(*) as count
            FROM memories
            WHERE cart_id = %s
            GROUP BY subject
            ORDER BY count DESC
            """,
            (cart_id,),
        )
        rows = cur.fetchall()
        subjects = [{"subject": row[0], "count": row[1]} for row in rows]

    return {"subjects": subjects, "total_subjects": len(subjects)}


def _get_stats_resource(conn: psycopg.Connection, cart_id: str) -> dict[str, Any]:
    """Get memory statistics."""
    with conn.cursor() as cur:
        # Total memory count
        cur.execute(
            "SELECT COUNT(*) FROM memories WHERE cart_id = %s",
            (cart_id,),
        )
        total_memories = cur.fetchone()[0]

        # Subject count
        cur.execute(
            "SELECT COUNT(DISTINCT subject) FROM memories WHERE cart_id = %s",
            (cart_id,),
        )
        total_subjects = cur.fetchone()[0]

        # Oldest and newest memory dates
        cur.execute(
            """
            SELECT MIN(created_at), MAX(created_at)
            FROM memories
            WHERE cart_id = %s
            """,
            (cart_id,),
        )
        date_row = cur.fetchone()
        oldest = date_row[0].isoformat() if date_row[0] else None
        newest = date_row[1].isoformat() if date_row[1] else None

        # Cart info
        cur.execute(
            "SELECT tag FROM carts WHERE id = %s",
            (cart_id,),
        )
        cart_row = cur.fetchone()
        cart_tag = cart_row[0] if cart_row else "unknown"

    return {
        "cart": cart_tag,
        "total_memories": total_memories,
        "total_subjects": total_subjects,
        "oldest_memory": oldest,
        "newest_memory": newest,
    }


def _get_recent_resource(conn: psycopg.Connection, cart_id: str) -> dict[str, Any]:
    """Get most recent memories."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, subject, content, created_at
            FROM memories
            WHERE cart_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (cart_id,),
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

    return {"memories": memories, "count": len(memories)}


def _get_subject_memories_resource(
    conn: psycopg.Connection, cart_id: str, subject: str
) -> dict[str, Any]:
    """Get all memories for a specific subject."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content, metadata, created_at
            FROM memories
            WHERE cart_id = %s AND subject = %s
            ORDER BY created_at DESC
            """,
            (cart_id, subject),
        )
        rows = cur.fetchall()
        memories = [
            {
                "id": str(row[0]),
                "content": row[1],
                "metadata": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in rows
        ]

    return {"subject": subject, "memories": memories, "count": len(memories)}


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
