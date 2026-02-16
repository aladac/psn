"""Memory management CLI commands."""

import json
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(invoke_without_command=True)
console = Console()

# Default auto-memory location (can be overridden)
DEFAULT_MEMORY_DIR = Path.home() / ".claude" / "memory"


@app.callback(invoke_without_command=True)
def memory_main(ctx: typer.Context) -> None:
    """Memory management commands."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


def get_memory_dir(project_path: str | None = None) -> Path:
    """Get the memory directory for a project."""
    if project_path:
        # Convert project path to Claude's memory path format
        safe_path = project_path.replace("/", "-").strip("-")
        return Path.home() / ".claude" / "projects" / safe_path / "memory"
    return DEFAULT_MEMORY_DIR


def extract_learnings(transcript_path: Path, last_n: int = 10) -> list[dict]:
    """Extract potential learnings from recent transcript entries."""
    learnings = []

    if not transcript_path.exists():
        return learnings

    # Read last N lines of transcript
    lines = transcript_path.read_text().strip().split("\n")
    recent = lines[-last_n:] if len(lines) > last_n else lines

    for line in recent:
        try:
            entry = json.loads(line)
            # Look for patterns indicating learnings
            if entry.get("type") == "user":
                text = entry.get("message", "").lower()
                # User corrections or preferences
                if any(kw in text for kw in ["always", "never", "remember", "don't forget", "preference"]):
                    learnings.append(
                        {
                            "type": "user_preference",
                            "content": entry.get("message"),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
            elif entry.get("type") == "assistant":
                # Check for important discoveries
                text = entry.get("message", "").lower()
                if any(kw in text for kw in ["learned", "discovered", "realized", "important"]):
                    learnings.append(
                        {
                            "type": "discovery",
                            "content": entry.get("message")[:500],  # Truncate
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
        except json.JSONDecodeError:
            continue

    return learnings


def append_to_memory(memory_dir: Path, learnings: list[dict]) -> int:
    """Append learnings to memory files. Returns count of items saved."""
    if not learnings:
        return 0

    memory_dir.mkdir(parents=True, exist_ok=True)

    # Append to a learnings log file
    log_file = memory_dir / "learnings.jsonl"

    saved = 0
    with log_file.open("a") as f:
        for learning in learnings:
            f.write(json.dumps(learning) + "\n")
            saved += 1

    return saved


@app.command("save")
def save() -> None:
    """Save memories from Stop hook (reads JSON from stdin)."""
    try:
        data = json.load(sys.stdin)
        transcript_path = data.get("transcript_path")
        cwd = data.get("cwd")

        if not transcript_path:
            return

        transcript = Path(transcript_path)
        learnings = extract_learnings(transcript)

        if learnings:
            memory_dir = get_memory_dir(cwd)
            count = append_to_memory(memory_dir, learnings)
            if count > 0:
                # Output for Claude to see
                print(json.dumps({"memories_saved": count}))
    except (json.JSONDecodeError, KeyError):
        pass


@app.command("list")
def list_memories(
    project: str = typer.Option(None, "--project", "-p", help="Project path"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries"),
) -> None:
    """List recent memories."""
    memory_dir = get_memory_dir(project)
    log_file = memory_dir / "learnings.jsonl"

    if not log_file.exists():
        console.print("[dim]No memories found[/dim]")
        return

    lines = log_file.read_text().strip().split("\n")
    recent = lines[-limit:] if len(lines) > limit else lines

    for line in reversed(recent):
        try:
            entry = json.loads(line)
            ts = entry.get("timestamp", "")[:10]
            typ = entry.get("type", "unknown")
            content = entry.get("content", "")[:80]
            console.print(f"[dim]{ts}[/dim] [{typ}] {content}...")
        except json.JSONDecodeError:
            continue


@app.command("clear")
def clear(
    project: str = typer.Option(None, "--project", "-p", help="Project path"),
) -> None:
    """Clear all memories."""
    memory_dir = get_memory_dir(project)
    log_file = memory_dir / "learnings.jsonl"

    if log_file.exists():
        log_file.unlink()
        console.print("[green]Memories cleared[/green]")
    else:
        console.print("[dim]No memories to clear[/dim]")
