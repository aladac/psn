"""Personality CLI."""

import typer
from rich.console import Console

from personality import __version__
from personality.cli import hooks

app = typer.Typer(
    name="psn",
    help="Personality - Infrastructure layer for Claude Code",
    no_args_is_help=True,
)
console = Console()

app.add_typer(hooks.app, name="hooks", help="Claude Code hooks management")


def version_callback(value: bool) -> None:
    if value:
        console.print(f"psn version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
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
    pass


@app.command()
def info() -> None:
    """Show personality info."""
    console.print(f"[bold]Personality[/bold] v{__version__}")
    console.print("Infrastructure layer for Claude Code")


if __name__ == "__main__":
    app()
