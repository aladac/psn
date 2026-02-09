"""MCP Prompts for Personality."""

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from personality.config import get_cart_identity, get_cart_voice
from personality.mcp.server import AppContext, mcp


def _get_ctx(ctx: Context[ServerSession, AppContext]) -> AppContext:
    """Extract typed AppContext from request context."""
    return ctx.request_context.lifespan_context


@mcp.prompt()
async def speak(
    text: str,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """
    Generate a speak command for the given text.

    Uses the current cart's voice and personality.

    Args:
        text: Text to speak
    """
    app = _get_ctx(ctx)

    voice = None
    persona_name = app.cart_name

    if app.cart_data:
        voice = get_cart_voice(app.cart_data)
        identity = get_cart_identity(app.cart_data)
        persona_name = identity.get("name", app.cart_name)

    voice_str = f" (voice: {voice})" if voice else ""

    return f"""Speak the following text as {persona_name}{voice_str}:

"{text}"

Use the `speak` tool to vocalize this text."""
