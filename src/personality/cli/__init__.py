"""Personality CLI."""

import typer
from rich.console import Console

from personality import __version__
from personality.cli import cart, context, decision, hooks, index, knowledge, memory, persona, tts

app = typer.Typer(
    name="psn",
    help="Personality - Infrastructure layer for Claude Code",
    invoke_without_command=True,
)
console = Console()

app.add_typer(hooks.app, name="hooks", help="Claude Code hooks management")
app.add_typer(context.app, name="context", help="Context tracking")
app.add_typer(index.app, name="index", help="Code indexing")
app.add_typer(memory.app, name="memory", help="Memory management")
app.add_typer(tts.app, name="tts", help="Text-to-speech")
app.add_typer(persona.app, name="persona", help="Persona training files")
app.add_typer(cart.app, name="cart", help="Cartridge management")
app.add_typer(knowledge.app, name="knowledge", help="Knowledge graph")
app.add_typer(decision.app, name="decision", help="Decision tracking")


def version_callback(value: bool) -> None:
    if value:
        console.print(f"psn version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Personality CLI."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def info() -> None:
    """Show personality info."""
    console.print(f"[bold]Personality[/bold] v{__version__}")
    console.print("Infrastructure layer for Claude Code")


if __name__ == "__main__":
    app()
