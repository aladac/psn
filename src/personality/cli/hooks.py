"""Hooks CLI commands."""

from pathlib import Path

import typer
from rich.console import Console

from personality.services.cart_registry import CartRegistry
from personality.services.persona_builder import PersonaBuilder

app = typer.Typer(invoke_without_command=True)
console = Console()

# Prompts directory (relative to project root)
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"


@app.callback(invoke_without_command=True)
def hooks_main(ctx: typer.Context) -> None:
    """Claude Code hooks management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


# Pre-tool-use hook
pre_tool_use_app = typer.Typer(help="Pre-tool-use hook", invoke_without_command=True)
app.add_typer(pre_tool_use_app, name="pre-tool-use")


@pre_tool_use_app.callback(invoke_without_command=True)
def pre_tool_use() -> None:
    """Hook called before tool execution."""
    pass


# Post-tool-use hook
post_tool_use_app = typer.Typer(help="Post-tool-use hook")
app.add_typer(post_tool_use_app, name="post-tool-use")


@post_tool_use_app.callback(invoke_without_command=True)
def post_tool_use() -> None:
    """Hook called after tool execution."""
    pass


# Stop hook
stop_app = typer.Typer(help="Stop hook")
app.add_typer(stop_app, name="stop")


@stop_app.callback(invoke_without_command=True)
def stop() -> None:
    """Hook called when agent stops."""
    pass


# Subagent-stop hook
subagent_stop_app = typer.Typer(help="Subagent-stop hook")
app.add_typer(subagent_stop_app, name="subagent-stop")


@subagent_stop_app.callback(invoke_without_command=True)
def subagent_stop() -> None:
    """Hook called when subagent stops."""
    pass


# Session-start hook
session_start_app = typer.Typer(help="Session-start hook")
app.add_typer(session_start_app, name="session-start")


@session_start_app.callback(invoke_without_command=True)
def session_start() -> None:
    """Hook called when session starts. Outputs intro prompt and persona instructions."""
    output_parts = []

    # Try to load active persona
    try:
        registry = CartRegistry()
        cart = registry.get_active()

        if cart:
            # Build persona instructions
            persona_instructions = PersonaBuilder.build_instructions(cart)
            if persona_instructions:
                output_parts.append(persona_instructions)
                output_parts.append("\n---\n\n")

            # Add persona summary to intro
            summary = PersonaBuilder.build_summary(cart)
            output_parts.append(f"**Active Persona:** {summary}\n\n")
    except Exception:
        # Silently continue if cart loading fails
        pass

    # Load base intro
    intro_file = PROMPTS_DIR / "intro.md"
    if intro_file.exists():
        output_parts.append(intro_file.read_text())

    # Output combined prompt
    if output_parts:
        print("".join(output_parts))


# Session-end hook
session_end_app = typer.Typer(help="Session-end hook")
app.add_typer(session_end_app, name="session-end")


@session_end_app.callback(invoke_without_command=True)
def session_end() -> None:
    """Hook called when session ends."""
    pass


# User-prompt-submit hook
user_prompt_submit_app = typer.Typer(help="User-prompt-submit hook")
app.add_typer(user_prompt_submit_app, name="user-prompt-submit")


@user_prompt_submit_app.callback(invoke_without_command=True)
def user_prompt_submit() -> None:
    """Hook called when user submits a prompt."""
    pass


# Pre-compact hook
pre_compact_app = typer.Typer(help="Pre-compact hook")
app.add_typer(pre_compact_app, name="pre-compact")


@pre_compact_app.callback(invoke_without_command=True)
def pre_compact() -> None:
    """Hook called before context compaction."""
    pass


# Notification hook
notification_app = typer.Typer(help="Notification hook")
app.add_typer(notification_app, name="notification")


@notification_app.callback(invoke_without_command=True)
def notification() -> None:
    """Hook called for notifications."""
    pass
