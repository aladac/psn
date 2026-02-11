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
        logger.warning("speak_voice_not_found: %s", e)
        return f"Voice not found: {voice_name}"
    except RuntimeError as e:
        logger.warning("speak_playback_error: %s", e)
        return f"Playback error: {e}"
    except Exception as e:
        logger.warning("speak_error: %s", e)
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


@mcp.tool()
async def project_search(
    query: str,
    limit: int = 5,
) -> str:
    """
    Search the current project's code index.

    Args:
        query: Search query for code
        limit: Maximum results to return (default 5)
    """
    from pathlib import Path

    from personality.index import get_indexer

    try:
        indexer = get_indexer(Path.cwd())
        results = indexer.search(query, k=limit)
        indexer.close()

        if not results:
            return "No matching code found. Is the project indexed? Run `psn index`"

        return _format_search_results(results)
    except Exception as e:
        logger.warning("project_search_error: %s", e)
        return f"Error searching project: {e}"


@mcp.tool()
async def project_summary() -> str:
    """Get the current project's summary from the index."""
    from pathlib import Path

    from personality.index import get_indexer

    try:
        indexer = get_indexer(Path.cwd())
        summary = indexer.get_summary()
        status = indexer.status()
        indexer.close()

        lines = [f"# Project: {status['project_path']}\n"]
        lines.append(f"- **Files indexed**: {status['file_count']}")
        lines.append(f"- **Code chunks**: {status['chunk_count']}")

        if summary:
            lines.append(f"\n## Summary\n\n{summary}")
        else:
            lines.append("\n*No summary generated yet.*")

        return "\n".join(lines)
    except Exception as e:
        logger.warning("project_summary_error: %s", e)
        return f"Error getting project summary: {e}"


def _format_search_results(results: list) -> str:
    """Format search results as markdown."""
    lines = []
    for r in results:
        name = r.name or r.chunk_type
        lines.append(f"**{r.file_path}:{r.start_line}** `{name}` (score: {r.score:.2f})")
        content_preview = r.content[:150].replace("\n", " ")
        lines.append(f"  {content_preview}...")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def cart_export(
    name: str,
    output_path: str,
    include_voice: bool = False,
) -> str:
    """
    Export a personality cart to portable format.

    Args:
        name: Cart name to export
        output_path: Output directory path
        include_voice: Include voice model (can be large)
    """
    from pathlib import Path

    from personality.cart import PortableCart

    try:
        output = Path(output_path)
        pcart = PortableCart.export(
            name,
            output,
            include_voice=include_voice,
            include_memories=True,
            as_zip=False,
        )
        manifest = pcart.manifest
        components = ", ".join(manifest.components.keys())
        return f"Exported cart '{name}' to {output_path}\nComponents: {components}"
    except Exception as e:
        logger.warning("cart_export_error: %s", e)
        return f"Error exporting cart: {e}"


@mcp.tool()
async def cart_import(
    path: str,
    mode: str = "safe",
    target_name: str | None = None,
) -> str:
    """
    Import a portable cart.

    Args:
        path: Path to .pcart directory or ZIP
        mode: Import mode (safe, override, merge, dry_run)
        target_name: Override cart name
    """
    from pathlib import Path

    from personality.cart import InstallMode, PortableCart

    try:
        input_path = Path(path)
        if not input_path.exists():
            return f"Error: Path not found: {path}"

        pcart = PortableCart.load(input_path)
        install_mode = InstallMode(mode)
        stats = pcart.install(mode=install_mode, target_name=target_name)
        pcart.cleanup()

        actions = "\n".join(f"- {a}" for a in stats["actions"])
        return f"Installed cart: {stats['cart_name']}\n\nActions:\n{actions}"
    except Exception as e:
        logger.warning("cart_import_error: %s", e)
        return f"Error importing cart: {e}"


@mcp.tool()
async def docs_search(
    query: str,
    limit: int = 5,
) -> str:
    """
    Search indexed documentation.

    Args:
        query: Search query
        limit: Maximum results to return (default 5)
    """
    from personality.docs import get_doc_indexer

    try:
        indexer = get_doc_indexer()
        results = indexer.search(query, k=limit)
        indexer.close()

        if not results:
            return "No matching documentation found. Run `psn docs index` to index docs."

        return _format_doc_results(results)
    except Exception as e:
        logger.warning("docs_search_error: %s", e)
        return f"Error searching docs: {e}"


@mcp.tool()
async def docs_index(
    path: str | None = None,
    force: bool = False,
) -> str:
    """
    Index a documentation directory.

    Args:
        path: Documentation directory path (default: ~/Projects/docs)
        force: Re-index all files even if unchanged
    """
    from pathlib import Path

    from personality.docs import get_doc_indexer

    try:
        docs_path = Path(path) if path else Path.home() / "Projects" / "docs"
        if not docs_path.exists():
            return f"Error: Path not found: {docs_path}"

        indexer = get_doc_indexer(docs_path)
        stats = indexer.index(force=force)
        indexer.close()

        return (
            f"Indexed {stats['files_indexed']} files, "
            f"{stats['chunks_created']} chunks "
            f"({stats['files_skipped']} unchanged)"
        )
    except Exception as e:
        logger.warning("docs_index_error: %s", e)
        return f"Error indexing docs: {e}"


def _format_doc_results(results: list) -> str:
    """Format doc search results as markdown."""
    lines = []
    for r in results:
        title = r.title or r.file_path
        lines.append(f"**{title}** (score: {r.score:.2f})")
        if r.heading:
            lines.append(f"  *{r.heading}*")
        content_preview = r.content[:200].replace("\n", " ")
        lines.append(f"  {content_preview}...")
        if r.source_url:
            lines.append(f"  Source: {r.source_url}")
        lines.append("")
    return "\n".join(lines)
