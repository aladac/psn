"""Knowledge-related MCP prompts."""

from mcp.types import GetPromptResult, PromptMessage, TextContent


async def knowledge_query(query: str) -> GetPromptResult:
    """
    Generate a prompt to query the knowledge graph.

    Args:
        query: Natural language query.

    Returns:
        GetPromptResult with knowledge query prompt.
    """
    prompt_text = f"""Query the knowledge graph for information about:

{query}

The knowledge graph stores facts as subject-predicate-object triples.
For example:
- "Python" - "is a" - "programming language"
- "FastAPI" - "built with" - "Starlette"

Search for relevant triples and synthesize the information into a helpful response.
If no relevant knowledge is found, say so and offer to help add new knowledge."""

    return GetPromptResult(
        description=f"Knowledge query: {query}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            )
        ],
    )
