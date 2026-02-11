"""MCP Server for Personality."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from personality.config import CONFIG_DIR, DEFAULT_VOICE_DIR, load_cart
from personality.memory import MemoryStore


@dataclass
class AppContext:
    """Application context for MCP tools."""

    cart_name: str
    cart_data: dict | None
    voice_dir: str
    memory: MemoryStore | None


def _get_active_cart() -> tuple[str, dict | None]:
    """Get the active cart name and data."""
    cart_name = os.environ.get("PERSONALITY_CART", "bt7274")
    cart_data = load_cart(cart_name)
    return cart_name, cart_data


def _get_memory_db_path(cart_name: str) -> Path:
    """Get the memory database path for a cart."""
    return CONFIG_DIR / "memory" / f"{cart_name}.db"


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle."""
    cart_name, cart_data = _get_active_cart()

    db_path = _get_memory_db_path(cart_name)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    memory = MemoryStore(db_path)

    try:
        yield AppContext(
            cart_name=cart_name,
            cart_data=cart_data,
            voice_dir=str(DEFAULT_VOICE_DIR),
            memory=memory,
        )
    finally:
        memory.close()


# Create the MCP server
mcp = FastMCP(
    "personality",
    lifespan=app_lifespan,
    instructions="""
Personality MCP server provides voice synthesis, memory, and persona management.

Tools:
- speak: Speak text aloud using the configured voice
- stop_speaking: Stop any currently playing audio
- remember: Store a memory with subject and content
- recall: Search memories by semantic similarity
- forget: Delete a specific memory by ID
- consolidate: Merge similar memories

Resources:
- personality://cart: Get current personality cart data
- personality://cart/{name}: Get specific cart by name
- personality://memories: List all memories
- personality://memories/{subject}: Get memories by subject prefix

Prompts:
- speak: Template for speaking text
""",
)


def create_server() -> FastMCP:
    """Create and return the MCP server instance."""
    return mcp


def run_server() -> None:
    """Run the MCP server with stdio transport."""
    # Import tools and resources to register them with the MCP server
    from personality.mcp import resources as _resources
    from personality.mcp import tools as _tools

    # Reference imports to register decorators
    _ = (_resources, _tools)

    mcp.run(transport="stdio")
