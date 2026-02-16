"""Memory-related MCP prompts."""

from mcp.types import GetPromptResult, PromptMessage, TextContent

# Subject taxonomy for memories
SUBJECT_TAXONOMY = """
Memory Subject Taxonomy:
- user.identity.* - User's name, title, preferences
- user.preference.* - User's coding style, tool preferences
- self.identity.* - Persona's identity traits
- self.trait.* - Persona's personality traits
- self.protocol.* - Behavioral protocols
- project.info.* - Project metadata, architecture
- project.decision.* - Architectural decisions
- knowledge.* - Domain knowledge, facts
- meta.note.* - Session notes, temporary context
"""


async def remember(subject: str, content: str) -> GetPromptResult:
    """
    Generate a prompt to store a memory.

    Args:
        subject: Memory subject (e.g., "user.preference.editor")
        content: What to remember.

    Returns:
        GetPromptResult with memory storage prompt.
    """
    # Suggest subject if not following taxonomy
    subject_suggestion = ""
    if not any(subject.startswith(p) for p in ["user.", "self.", "project.", "knowledge.", "meta."]):
        subject_suggestion = f"""
Note: The subject "{subject}" doesn't follow the standard taxonomy.
Consider using one of these prefixes:
- user.* for user-related info
- project.* for project-related info
- knowledge.* for general knowledge
"""

    prompt_text = f"""Store the following as a memory:

**Subject:** {subject}
**Content:** {content}
{subject_suggestion}
{SUBJECT_TAXONOMY}

Confirm the memory has been stored and suggest any refinements to the subject categorization if needed."""

    return GetPromptResult(
        description=f"Store memory: {subject}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            )
        ],
    )
