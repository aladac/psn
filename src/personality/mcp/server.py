"""MCP Server for Personality."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from personality.config import DEFAULT_VOICE_DIR, load_cart


@dataclass
class AppContext:
    """Application context for MCP tools."""

    cart_name: str
    cart_data: dict | None
    voice_dir: str


def _get_active_cart() -> tuple[str, dict | None]:
    """Get the active cart name and data."""
    import os

    cart_name = os.environ.get("PERSONALITY_CART", "bt7274")
    cart_data = load_cart(cart_name)
    return cart_name, cart_data


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle."""
    cart_name, cart_data = _get_active_cart()

    yield AppContext(
        cart_name=cart_name,
        cart_data=cart_data,
        voice_dir=str(DEFAULT_VOICE_DIR),
    )


# Create the MCP server
mcp = FastMCP(
    "personality",
    lifespan=app_lifespan,
    instructions="""
Personality MCP server provides voice synthesis and persona management.

Tools:
- speak: Speak text aloud using the configured voice

Resources:
- personality://cart: Get current personality cart data
- personality://cart/{name}: Get specific cart by name

Prompts:
- speak: Template for speaking text
""",
)


def create_server() -> FastMCP:
    """Create and return the MCP server instance."""
    return mcp


def run_server() -> None:
    """Run the MCP server with stdio transport."""
    # Import tools and resources to register them
    from personality.mcp import resources, tools  # noqa: F401

    mcp.run(transport="stdio")
