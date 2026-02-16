"""Memory management CLI commands."""

import json
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from personality.services.memory_consolidator import MemoryConsolidator
from personality.services.memory_extractor import MemoryExtractor
from personality.services.memory_pruner import MemoryPruner

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


@app.command("extract")
def extract_memories(
    text: str = typer.Argument(None, help="Text to extract from (or stdin)"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-c", help="Minimum confidence"),
) -> None:
    """Extract memories from text."""
    if text is None:
        text = sys.stdin.read()

    extractor = MemoryExtractor(min_confidence=min_confidence)
    memories = extractor.extract_from_text(text)

    if not memories:
        console.print("[yellow]No memories extracted.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Extracted Memories")
    table.add_column("Subject", style="cyan")
    table.add_column("Content")
    table.add_column("Confidence", justify="right")

    for mem in memories:
        table.add_row(
            mem.subject,
            mem.content[:60] + "..." if len(mem.content) > 60 else mem.content,
            f"{mem.confidence:.2f}",
        )

    console.print(table)


@app.command("consolidate")
def consolidate_memories(
    project: str = typer.Option(None, "--project", "-p", help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without changes"),
    threshold: float = typer.Option(0.6, "--threshold", "-t", help="Similarity threshold"),
) -> None:
    """Consolidate similar memories."""
    memory_dir = get_memory_dir(project)
    log_file = memory_dir / "learnings.jsonl"

    if not log_file.exists():
        console.print("[yellow]No memories to consolidate.[/yellow]")
        raise typer.Exit(0)

    # Load memories
    memories = []
    for line in log_file.read_text().strip().split("\n"):
        try:
            memories.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if len(memories) < 2:
        console.print("[yellow]Not enough memories to consolidate.[/yellow]")
        raise typer.Exit(0)

    # Consolidate
    consolidator = MemoryConsolidator(similarity_threshold=threshold)
    consolidated, result = consolidator.consolidate(memories)

    console.print("[bold]Consolidation Results:[/bold]")
    console.print(f"  Original: {result.original_count}")
    console.print(f"  Merged:   {result.merged_count}")
    console.print(f"  Final:    {result.final_count}")
    console.print(f"  Reduced:  {result.reduction} ({result.reduction_percent:.1f}%)")

    if dry_run:
        console.print("\n[dim]Dry run - no changes made[/dim]")
        return

    if result.reduction > 0:
        # Write consolidated memories
        with log_file.open("w") as f:
            for mem in consolidated:
                f.write(json.dumps(mem) + "\n")
        console.print(f"\n[green]Consolidated {result.reduction} memories.[/green]")
    else:
        console.print("\n[dim]No consolidation needed.[/dim]")


@app.command("prune")
def prune_memories(
    project: str = typer.Option(None, "--project", "-p", help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without changes"),
    threshold: float = typer.Option(0.3, "--threshold", "-t", help="Prune threshold"),
    archive: bool = typer.Option(True, "--archive/--no-archive", help="Archive pruned memories"),
) -> None:
    """Prune low-value memories."""
    memory_dir = get_memory_dir(project)
    log_file = memory_dir / "learnings.jsonl"

    if not log_file.exists():
        console.print("[yellow]No memories to prune.[/yellow]")
        raise typer.Exit(0)

    # Load memories
    memories = []
    for line in log_file.read_text().strip().split("\n"):
        try:
            memories.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not memories:
        console.print("[yellow]No memories to prune.[/yellow]")
        raise typer.Exit(0)

    # Prune
    pruner = MemoryPruner(prune_threshold=threshold)
    retained, pruned, result = pruner.prune(memories, archive=archive)

    console.print("[bold]Pruning Results:[/bold]")
    console.print(f"  Total:    {result.total_count}")
    console.print(f"  Retained: {result.retained_count}")
    console.print(f"  Pruned:   {result.pruned_count} ({result.pruned_percent:.1f}%)")

    if pruned and result.pruned_count <= 10:
        console.print("\n[dim]Pruned memories:[/dim]")
        for p in result.pruned_memories:
            console.print(f"  [{p.get('score', 0):.2f}] {p.get('subject', '')}")

    if dry_run:
        console.print("\n[dim]Dry run - no changes made[/dim]")
        return

    if result.pruned_count > 0:
        # Write retained memories
        with log_file.open("w") as f:
            for mem in retained:
                f.write(json.dumps(mem) + "\n")

        # Archive pruned if requested
        if archive and pruned:
            archive_file = memory_dir / "archived.jsonl"
            with archive_file.open("a") as f:
                for mem in pruned:
                    mem["archived_at"] = datetime.now().isoformat()
                    f.write(json.dumps(mem) + "\n")
            console.print(f"\n[green]Archived {len(pruned)} memories to {archive_file.name}[/green]")

        console.print(f"[green]Pruned {result.pruned_count} memories.[/green]")
    else:
        console.print("\n[dim]No pruning needed.[/dim]")


@app.command("hook-precompact")
def hook_precompact() -> None:
    """PreCompact hook: consolidate and prune memories."""
    try:
        data = json.load(sys.stdin)
        cwd = data.get("cwd")

        memory_dir = get_memory_dir(cwd)
        log_file = memory_dir / "learnings.jsonl"

        if not log_file.exists():
            return

        # Load memories
        memories = []
        for line in log_file.read_text().strip().split("\n"):
            try:
                memories.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if len(memories) < 5:
            return  # Not enough to consolidate

        # Consolidate
        consolidator = MemoryConsolidator()
        consolidated, cons_result = consolidator.consolidate(memories)

        # Prune
        pruner = MemoryPruner()
        retained, pruned, prune_result = pruner.prune(consolidated)

        # Write results
        if cons_result.reduction > 0 or prune_result.pruned_count > 0:
            with log_file.open("w") as f:
                for mem in retained:
                    f.write(json.dumps(mem) + "\n")

            # Archive pruned
            if pruned:
                archive_file = memory_dir / "archived.jsonl"
                with archive_file.open("a") as f:
                    for mem in pruned:
                        mem["archived_at"] = datetime.now().isoformat()
                        f.write(json.dumps(mem) + "\n")

            # Output summary
            print(
                json.dumps(
                    {
                        "consolidated": cons_result.reduction,
                        "pruned": prune_result.pruned_count,
                        "retained": len(retained),
                    }
                )
            )

    except (json.JSONDecodeError, KeyError):
        pass
