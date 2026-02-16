"""Persona-related MCP prompts."""

from mcp.types import GetPromptResult, PromptMessage, TextContent

from personality.services.cart_registry import CartRegistry
from personality.services.persona_builder import PersonaBuilder


async def persona_greeting(user_name: str | None = None) -> GetPromptResult:
    """
    Generate an in-character greeting.

    Args:
        user_name: Optional name to address the user by.

    Returns:
        GetPromptResult with greeting prompt.
    """
    registry = CartRegistry()
    cart = registry.get_active()

    if not cart:
        return GetPromptResult(
            description="No active persona",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text="Generate a friendly greeting."),
                )
            ],
        )

    greeting = PersonaBuilder.build_greeting(cart, user_name)
    identity = cart.preferences.identity

    prompt_text = f"""You are {identity.name or cart.tag}.
{f"Type: {identity.type}" if identity.type else ""}
{f'Tagline: "{identity.tagline}"' if identity.tagline else ""}

Generate a greeting in character. Here's an example of how you greet:
{greeting}

Now greet {user_name or "the user"} in your characteristic style."""

    return GetPromptResult(
        description=f"In-character greeting from {identity.name or cart.tag}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            )
        ],
    )


async def in_character(question: str) -> GetPromptResult:
    """
    Frame a question for an in-character response.

    Args:
        question: The question to answer in character.

    Returns:
        GetPromptResult with in-character prompt.
    """
    registry = CartRegistry()
    cart = registry.get_active()

    if not cart:
        return GetPromptResult(
            description="No active persona",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=question),
                )
            ],
        )

    instructions = PersonaBuilder.build_instructions(cart)
    identity = cart.preferences.identity

    prompt_text = f"""{instructions}

---

Now, staying fully in character as {identity.name or cart.tag}, respond to:

{question}"""

    return GetPromptResult(
        description=f"In-character response from {identity.name or cart.tag}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            )
        ],
    )
