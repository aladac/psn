"""MCP Resources for Personality."""

import logging

from personality.config import (
    get_cart_identity,
    get_cart_voice,
    list_carts,
    load_cart,
)
from personality.mcp.server import mcp

logger = logging.getLogger(__name__)


@mcp.resource("personality://cart")
def get_current_cart() -> str:
    """
    Get the current personality cart data.

    Returns the active cart's identity, voice, and memories.
    """
    import os

    cart_name = os.environ.get("PERSONALITY_CART", "bt7274")
    return _format_cart(cart_name)


@mcp.resource("personality://cart/{name}")
def get_cart_by_name(name: str) -> str:
    """
    Get a personality cart by name.

    Args:
        name: Cart name (without .yml extension)
    """
    return _format_cart(name)


@mcp.resource("personality://carts")
def list_available_carts() -> str:
    """List all available personality carts."""
    cart_names = list_carts()

    if not cart_names:
        return "No carts found in ~/.config/personality/carts/"

    lines = ["# Available Carts\n"]
    for name in sorted(cart_names):
        cart_data = load_cart(name)
        if cart_data:
            identity = get_cart_identity(cart_data)
            display_name = identity.get("name", name)
            voice = get_cart_voice(cart_data) or "default"
            lines.append(f"- **{name}**: {display_name} (voice: {voice})")
        else:
            lines.append(f"- **{name}**: (failed to load)")

    return "\n".join(lines)


def _format_cart(name: str) -> str:
    """Format cart data as markdown."""
    cart_data = load_cart(name)

    if not cart_data:
        return f"Cart not found: {name}"

    identity = get_cart_identity(cart_data)
    voice = get_cart_voice(cart_data)

    lines = [f"# {identity.get('name', name)}"]

    # Identity section
    if identity:
        lines.append("\n## Identity\n")
        for key, value in identity.items():
            if key != "name":
                lines.append(f"- **{key}**: {value}")

    # Voice
    if voice:
        lines.append(f"\n## Voice\n\nConfigured voice: `{voice}`")

    # Memories
    memories = cart_data.get("memories", [])
    if memories:
        lines.append("\n## Memories\n")
        for mem in memories[:10]:  # Limit to first 10
            subject = mem.get("subject", "unknown")
            content = mem.get("content", "")
            if isinstance(content, list):
                content = ", ".join(str(c) for c in content)
            lines.append(f"- **{subject}**: {content[:100]}")
        if len(memories) > 10:
            lines.append(f"\n*...and {len(memories) - 10} more memories*")

    return "\n".join(lines)
