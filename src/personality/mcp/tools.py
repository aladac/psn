"""MCP Tools for Personality."""

import logging
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from personality.config import get_cart_voice
from personality.mcp.server import AppContext, mcp
from personality.memory import Memory
from personality.speak import Speak

logger = logging.getLogger(__name__)

DEFAULT_RECALL_LIMIT = 5


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


@mcp.tool()
async def stop_speaking() -> str:
    """Stop any currently playing audio."""
    stopped = Speak.stop()
    if stopped:
        return "Stopped audio playback"
    return "No audio was playing"


@mcp.tool()
async def remember(
    subject: str,
    content: str,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """
    Store a memory for later recall.

    Args:
        subject: Category/topic (e.g., "user.preferences", "project.decisions")
        content: The information to remember
    """
    app = _get_ctx(ctx)
    if not app.memory:
        return "Error: Memory store not initialized"

    memory_id = app.memory.remember(subject, content, source="mcp")
    return f"Remembered (id={memory_id}): {subject}"


@mcp.tool()
async def recall(
    query: str,
    ctx: Context[ServerSession, AppContext],
    limit: int = DEFAULT_RECALL_LIMIT,
) -> str:
    """
    Search memories by semantic similarity.

    Args:
        query: Search query
        limit: Maximum results to return (default 5)
    """
    app = _get_ctx(ctx)
    if not app.memory:
        return "Error: Memory store not initialized"

    memories = app.memory.recall(query, k=limit)
    if not memories:
        return "No relevant memories found"

    return _format_memories(memories)


@mcp.tool()
async def forget(
    memory_id: int,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """
    Delete a specific memory by ID.

    Args:
        memory_id: The memory ID to delete
    """
    app = _get_ctx(ctx)
    if not app.memory:
        return "Error: Memory store not initialized"

    if app.memory.forget(memory_id):
        return f"Forgot memory {memory_id}"
    return f"Memory {memory_id} not found"


@mcp.tool()
async def consolidate(
    ctx: Context[ServerSession, AppContext],
    threshold: float = 0.92,
) -> str:
    """
    Merge similar memories to reduce redundancy.

    Args:
        threshold: Similarity threshold for merging (0.0-1.0, default 0.92)
    """
    app = _get_ctx(ctx)
    if not app.memory:
        return "Error: Memory store not initialized"

    merged = app.memory.consolidate(threshold)
    return f"Consolidated {merged} memories"


def _format_memories(memories: list[Memory]) -> str:
    """Format memories as markdown."""
    lines = []
    for mem in memories:
        lines.append(f"**[{mem.id}] {mem.subject}** (score: {mem.score:.2f})")
        lines.append(f"  {mem.content[:200]}{'...' if len(mem.content) > 200 else ''}")
        lines.append("")
    return "\n".join(lines)
