"""MCP Tools for Personality."""

import logging
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from personality.config import get_cart_voice
from personality.mcp.server import AppContext, mcp
from personality.speak import Speak

logger = logging.getLogger(__name__)


def _get_ctx(ctx: Context[ServerSession, AppContext]) -> AppContext:
    """Extract typed AppContext from request context."""
    return ctx.request_context.lifespan_context


@mcp.tool()
async def speak(
    text: str,
    ctx: Context[ServerSession, AppContext],
    voice: str | None = None,
) -> str:
    """
    Speak text aloud using the configured personality voice.

    Args:
        text: Text to speak
        voice: Optional voice override (defaults to cart voice)
    """
    app = _get_ctx(ctx)

    if not text.strip():
        return "Error: No text provided"

    # Resolve voice from cart or override
    voice_name = voice
    if not voice_name and app.cart_data:
        voice_name = get_cart_voice(app.cart_data)
    if not voice_name:
        voice_name = app.cart_name

    try:
        speaker = Speak(Path(app.voice_dir))
        speaker.say(text, voice_name)
        return f"Spoke: {text[:50]}{'...' if len(text) > 50 else ''}"
    except FileNotFoundError as e:
        logger.warning("speak_voice_not_found", error=str(e))
        return f"Voice not found: {voice_name}"
    except RuntimeError as e:
        logger.warning("speak_playback_error", error=str(e))
        return f"Playback error: {e}"
    except Exception as e:
        logger.warning("speak_error", error=str(e))
        return f"Error: {e}"
