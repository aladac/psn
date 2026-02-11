"""MCP Prompts for Personality."""

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from personality.config import get_cart_identity, get_cart_voice
from personality.mcp.server import AppContext, mcp


def _get_ctx(ctx: Context[ServerSession, AppContext]) -> AppContext:
    """Extract typed AppContext from request context."""
    return ctx.request_context.lifespan_context


def _get_memories_by_prefix(app: AppContext, prefix: str, limit: int = 10) -> list:
    """Get memories starting with a subject prefix."""
    if not app.memory:
        return []
    all_memories = app.memory.list_all()
    return [m for m in all_memories if m.subject.startswith(prefix)][:limit]


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


@mcp.prompt()
async def persona_scaffold(ctx: Context[ServerSession, AppContext]) -> str:
    """
    Generate complete persona context scaffold.

    Loads the cart's identity, traits, and communication style,
    then fetches self.* memories for accumulated personality data.
    """
    app = _get_ctx(ctx)

    lines = ["# Persona Context\n"]

    # Load identity from cart
    if app.cart_data:
        identity = get_cart_identity(app.cart_data)
        if identity:
            lines.append("## Identity\n")
            lines.append(f"- **Name**: {identity.get('name', app.cart_name)}")
            if identity.get("tagline"):
                lines.append(f"- **Tagline**: {identity['tagline']}")
            if identity.get("description"):
                lines.append(f"- **Description**: {identity['description']}")
            lines.append("")

        # Check for traits in cart data
        prefs = app.cart_data.get("preferences", {})
        if prefs.get("traits"):
            lines.append("## Traits\n")
            for trait in prefs["traits"]:
                lines.append(f"- {trait}")
            lines.append("")

        if prefs.get("communication_style"):
            lines.append("## Communication Style\n")
            style = prefs["communication_style"]
            if isinstance(style, dict):
                for key, val in style.items():
                    lines.append(f"- **{key}**: {val}")
            else:
                lines.append(str(style))
            lines.append("")

    # Fetch self.* memories
    self_memories = _get_memories_by_prefix(app, "self.")
    if self_memories:
        lines.append("## Self Knowledge\n")
        for mem in self_memories:
            subject_suffix = mem.subject.replace("self.", "")
            lines.append(f"### {subject_suffix}\n")
            lines.append(f"{mem.content}\n")

    if len(lines) == 1:
        lines.append("*No persona data configured. Load a cart with identity.*")

    return "\n".join(lines)


@mcp.prompt()
async def conversation_starter(ctx: Context[ServerSession, AppContext]) -> str:
    """
    Initialize conversation with user context.

    Fetches user.* memories and recent session context
    to provide continuity across interactions.
    """
    app = _get_ctx(ctx)

    lines = ["# Conversation Context\n"]

    # User memories
    user_memories = _get_memories_by_prefix(app, "user.")
    if user_memories:
        lines.append("## User Information\n")
        for mem in user_memories:
            subject_suffix = mem.subject.replace("user.", "")
            lines.append(f"- **{subject_suffix}**: {mem.content}")
        lines.append("")

    # Session memories
    session_memories = _get_memories_by_prefix(app, "session.", limit=5)
    if session_memories:
        lines.append("## Recent Sessions\n")
        for mem in session_memories:
            lines.append(f"- {mem.content[:100]}...")
        lines.append("")

    # Guidelines
    lines.append("## Guidelines\n")
    lines.append("- Reference user context naturally without repeating it back")
    lines.append("- Build on previous interactions when relevant")
    lines.append("- Ask clarifying questions rather than assuming")
    lines.append("- Use the user's preferred terminology and style")

    return "\n".join(lines)


@mcp.prompt()
async def learning_interaction(
    topic: str,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """
    Knowledge extraction template for learning new information.

    Args:
        topic: The topic to learn about
    """
    return f"""# Learning: {topic}

## Subject Hierarchy Guide

Structure learned information using dot notation:
- `user.name` - User's name
- `user.preferences.editor` - User's preferred editor
- `project.stack` - Current project's tech stack
- `self.capabilities.{topic}` - Own capabilities related to topic

## Extraction Guidelines

When learning from this interaction:
1. **Identify facts**: Extract concrete, verifiable information
2. **Note preferences**: Capture stated likes/dislikes/preferences
3. **Record context**: Include relevant situational context
4. **Avoid assumptions**: Only store explicitly stated information

## Example Extractions

For "I prefer dark themes in my editor":
- Subject: `user.preferences.theme`
- Content: `Prefers dark themes in editor`

For "The project uses FastAPI and PostgreSQL":
- Subject: `project.stack`
- Content: `FastAPI backend with PostgreSQL database`

## Current Topic: {topic}

Extract relevant information about this topic and use the `remember` tool
to store useful facts with appropriate subjects."""


@mcp.prompt()
async def project_overview(ctx: Context[ServerSession, AppContext]) -> str:
    """
    Comprehensive project context from index and memories.

    Loads the project index summary and fetches project.* memories
    to provide complete project understanding.
    """
    app = _get_ctx(ctx)

    lines = ["# Project Overview\n"]

    # Try to load project index
    try:
        from pathlib import Path

        from personality.index import get_indexer

        indexer = get_indexer(Path.cwd())
        status = indexer.status()
        summary = indexer.get_summary()
        indexer.close()

        lines.append("## Index Status\n")
        lines.append(f"- **Path**: {status['project_path']}")
        lines.append(f"- **Files**: {status['file_count']}")
        lines.append(f"- **Code chunks**: {status['chunk_count']}")
        lines.append("")

        if summary:
            lines.append("## Project Summary\n")
            lines.append(summary)
            lines.append("")
    except Exception:
        lines.append("*Project not indexed. Run `psn index` to enable search.*\n")

    # Project memories
    project_memories = _get_memories_by_prefix(app, "project.")
    if project_memories:
        lines.append("## Project Knowledge\n")
        for mem in project_memories:
            subject_suffix = mem.subject.replace("project.", "")
            lines.append(f"### {subject_suffix}\n")
            lines.append(f"{mem.content}\n")

    # Available actions
    lines.append("## Available Actions\n")
    lines.append("- `project_search(query)` - Search code semantically")
    lines.append("- `project_summary()` - Get index summary")
    lines.append("- `remember(subject, content)` - Store project knowledge")
    lines.append("- `recall(query)` - Retrieve relevant memories")

    return "\n".join(lines)


@mcp.prompt()
async def decision_support(
    decision: str,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """
    Structured decision-making framework with relevant context.

    Args:
        decision: The decision to be made
    """
    app = _get_ctx(ctx)

    lines = [f"# Decision: {decision}\n"]

    # Fetch potentially relevant memories
    if app.memory:
        relevant = app.memory.recall(decision, k=5, threshold=0.3)
        if relevant:
            lines.append("## Relevant Context\n")
            for mem in relevant:
                lines.append(f"- **{mem.subject}**: {mem.content[:150]}...")
            lines.append("")

    # Decision framework
    lines.append("## Decision Framework\n")
    lines.append("### 1. Define the Problem")
    lines.append(f"- Core question: {decision}")
    lines.append("- What constraints exist?")
    lines.append("- Who is affected?\n")

    lines.append("### 2. Gather Information")
    lines.append("- What do we know?")
    lines.append("- What assumptions are we making?")
    lines.append("- What information is missing?\n")

    lines.append("### 3. Identify Options")
    lines.append("- Option A: ...")
    lines.append("- Option B: ...")
    lines.append("- Option C: Do nothing\n")

    lines.append("### 4. Evaluate Trade-offs")
    lines.append("| Option | Pros | Cons | Risk |")
    lines.append("|--------|------|------|------|")
    lines.append("| A | | | |")
    lines.append("| B | | | |\n")

    lines.append("### 5. Decide and Document")
    lines.append("- Selected option: ...")
    lines.append("- Rationale: ...")
    lines.append("- Next steps: ...\n")

    lines.append("## After Decision")
    lines.append("Store the decision using:")
    lines.append(f'`remember("decision.{decision[:20]}", "Decision: ... Rationale: ...")`')

    return "\n".join(lines)
