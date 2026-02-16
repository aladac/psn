"""Context tracking CLI commands."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(invoke_without_command=True)
console = Console()

CONTEXT_DIR = Path("/tmp/psn-context")


def get_session_file(session_id: str) -> Path:
    """Get the context file path for a session."""
    CONTEXT_DIR.mkdir(exist_ok=True)
    return CONTEXT_DIR / f"{session_id}.json"


def load_context(session_id: str) -> dict:
    """Load context data for a session."""
    session_file = get_session_file(session_id)
    if session_file.exists():
        return json.loads(session_file.read_text())
    return {"files": []}


def save_context(session_id: str, context: dict) -> None:
    """Save context data for a session."""
    session_file = get_session_file(session_id)
    session_file.write_text(json.dumps(context, indent=2))


@app.callback(invoke_without_command=True)
def context_main(ctx: typer.Context) -> None:
    """Context tracking commands."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("track-read")
def track_read() -> None:
    """Track a file read from PostToolUse hook (reads JSON from stdin)."""
    try:
        data = json.load(sys.stdin)
        session_id = data.get("session_id", "unknown")
        file_path = data.get("tool_input", {}).get("file_path")

        if file_path:
            context = load_context(session_id)
            if file_path not in context["files"]:
                context["files"].append(file_path)
                save_context(session_id, context)
    except (json.JSONDecodeError, KeyError):
        pass  # Silently ignore invalid input


@app.command("check")
def check(
    file_path: str = typer.Argument(..., help="File path to check"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID"),
) -> None:
    """Check if a file is already in context."""
    if session_id is None:
        # Try to find most recent session
        if CONTEXT_DIR.exists():
            sessions = sorted(CONTEXT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if sessions:
                session_id = sessions[0].stem

    if session_id is None:
        console.print("[yellow]No session found[/yellow]")
        raise typer.Exit(1)

    context = load_context(session_id)
    abs_path = str(Path(file_path).resolve())

    if abs_path in context["files"] or file_path in context["files"]:
        console.print(f"[green]✓[/green] {file_path} is in context")
    else:
        console.print(f"[dim]✗[/dim] {file_path} not in context")
        raise typer.Exit(1)


@app.command("list")
def list_files(
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID"),
) -> None:
    """List all files in context."""
    if session_id is None:
        if CONTEXT_DIR.exists():
            sessions = sorted(CONTEXT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if sessions:
                session_id = sessions[0].stem

    if session_id is None:
        console.print("[yellow]No session found[/yellow]")
        raise typer.Exit(0)

    context = load_context(session_id)

    if not context["files"]:
        console.print("[dim]No files in context[/dim]")
    else:
        console.print(f"[bold]Files in context[/bold] ({len(context['files'])})")
        for f in context["files"]:
            console.print(f"  {f}")


@app.command("clear")
def clear(
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID"),
) -> None:
    """Clear context for a session."""
    if session_id is None:
        if CONTEXT_DIR.exists():
            sessions = sorted(CONTEXT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if sessions:
                session_id = sessions[0].stem

    if session_id:
        session_file = get_session_file(session_id)
        if session_file.exists():
            session_file.unlink()
        console.print("[green]Context cleared[/green]")
    else:
        console.print("[yellow]No session to clear[/yellow]")
