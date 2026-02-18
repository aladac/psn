"""Knowledge CLI commands."""

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from personality.services.knowledge import KnowledgeService

app = typer.Typer(
    name="knowledge",
    help="Knowledge graph management",
    invoke_without_command=True,
)
console = Console()


def get_service() -> KnowledgeService:
    """Get the knowledge service."""
    return KnowledgeService()


@app.callback(invoke_without_command=True)
def knowledge_main(ctx: typer.Context) -> None:
    """Knowledge graph management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("add")
def add_knowledge(
    subject: str = typer.Argument(..., help="Subject (e.g., 'Python')"),
    predicate: str = typer.Argument(..., help="Predicate (e.g., 'is a')"),
    obj: str = typer.Argument(..., help="Object (e.g., 'programming language')"),
    source: str = typer.Option("", "--source", "-s", help="Source of knowledge"),
    confidence: float = typer.Option(1.0, "--confidence", "-c", help="Confidence (0.0-1.0)"),
) -> None:
    """Add a knowledge triple (subject-predicate-object)."""
    service = get_service()

    triple = service.add(
        subject=subject,
        predicate=predicate,
        obj=obj,
        source=source,
        confidence=confidence,
    )

    console.print(f"[green]Added:[/green] {triple.to_sentence()}")
    console.print(f"[dim]ID: {triple.id}[/dim]")


@app.command("query")
def query_knowledge(
    subject: str = typer.Option(None, "--subject", "-s", help="Filter by subject"),
    predicate: str = typer.Option(None, "--predicate", "-p", help="Filter by predicate"),
    obj: str = typer.Option(None, "--object", "-o", help="Filter by object"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results"),
) -> None:
    """Query knowledge triples by filters."""
    service = get_service()

    results = service.query(subject=subject, predicate=predicate, obj=obj)
    results = results[:limit]

    if not results:
        console.print("[yellow]No matching triples found.[/yellow]")
        raise typer.Exit(0)

    _print_triples(results)


@app.command("search")
def search_knowledge(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results"),
) -> None:
    """Search knowledge triples by text."""
    service = get_service()

    results = service.search(query, limit=limit)

    if not results:
        console.print("[yellow]No matching triples found.[/yellow]")
        raise typer.Exit(0)

    _print_triples(results)


@app.command("list")
def list_knowledge(
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results"),
) -> None:
    """List all knowledge triples."""
    service = get_service()

    results = service.list_all(limit=limit)

    if not results:
        console.print("[yellow]No knowledge stored yet.[/yellow]")
        console.print("\nAdd some knowledge:")
        console.print('  psn knowledge add "Python" "is a" "programming language"')
        raise typer.Exit(0)

    _print_triples(results)
    console.print(f"\n[dim]Total: {service.count()} triples[/dim]")


@app.command("show")
def show_triple(
    triple_id: str = typer.Argument(..., help="Triple ID"),
) -> None:
    """Show details of a knowledge triple."""
    service = get_service()

    triple = service.get(triple_id)
    if not triple:
        console.print(f"[red]Triple not found:[/red] {triple_id}")
        raise typer.Exit(1)

    console.print(f"\n[bold]{triple.to_sentence()}[/bold]")
    console.print(f"\n[dim]ID:[/dim] {triple.id}")
    console.print(f"[dim]Subject:[/dim] {triple.subject}")
    console.print(f"[dim]Predicate:[/dim] {triple.predicate}")
    console.print(f"[dim]Object:[/dim] {triple.object}")
    if triple.source:
        console.print(f"[dim]Source:[/dim] {triple.source}")
    console.print(f"[dim]Confidence:[/dim] {triple.confidence:.2f}")
    console.print(f"[dim]Created:[/dim] {triple.created_at}")


@app.command("remove")
def remove_triple(
    triple_id: str = typer.Argument(..., help="Triple ID to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a knowledge triple."""
    service = get_service()

    triple = service.get(triple_id)
    if not triple:
        console.print(f"[red]Triple not found:[/red] {triple_id}")
        raise typer.Exit(1)

    if not force:
        console.print(f"Remove: {triple.to_sentence()}")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            raise typer.Exit(0)

    service.remove(triple_id)
    console.print(f"[green]Removed:[/green] {triple_id}")


@app.command("clear")
def clear_knowledge(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Clear all knowledge triples."""
    service = get_service()

    count = service.count()
    if count == 0:
        console.print("[yellow]No knowledge to clear.[/yellow]")
        raise typer.Exit(0)

    if not force:
        confirm = typer.confirm(f"Clear all {count} triples?")
        if not confirm:
            raise typer.Exit(0)

    removed = service.clear()
    console.print(f"[green]Cleared {removed} triples.[/green]")


@app.command("subjects")
def list_subjects() -> None:
    """List unique subjects."""
    service = get_service()

    subjects = service.subjects()
    if not subjects:
        console.print("[yellow]No subjects found.[/yellow]")
        raise typer.Exit(0)

    console.print("[bold]Subjects:[/bold]")
    for subject in subjects:
        console.print(f"  {subject}")


@app.command("predicates")
def list_predicates() -> None:
    """List unique predicates."""
    service = get_service()

    predicates = service.predicates()
    if not predicates:
        console.print("[yellow]No predicates found.[/yellow]")
        raise typer.Exit(0)

    console.print("[bold]Predicates:[/bold]")
    for predicate in predicates:
        console.print(f"  {predicate}")


@app.command("export")
def export_knowledge() -> None:
    """Export knowledge as sentences."""
    service = get_service()

    sentences = service.export_sentences()
    if not sentences:
        console.print("[yellow]No knowledge to export.[/yellow]")
        raise typer.Exit(0)

    for sentence in sentences:
        print(sentence)


def _print_triples(triples: list) -> None:
    """Print a list of triples as a table."""
    table = Table(title="Knowledge Triples")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Subject", style="cyan")
    table.add_column("Predicate", style="green")
    table.add_column("Object", style="yellow")

    for triple in triples:
        table.add_row(
            triple.id,
            triple.subject,
            triple.predicate,
            triple.object,
        )

    console.print(table)


@app.command("hook")
def hook_stop() -> None:
    """Extract knowledge from Stop hook (reads JSON from stdin)."""
    try:
        data = json.load(sys.stdin)
        transcript_path = data.get("transcript_path")

        if not transcript_path:
            return

        from pathlib import Path

        transcript = Path(transcript_path)
        if not transcript.exists():
            return

        # Read recent transcript entries looking for knowledge patterns
        lines = transcript.read_text().strip().split("\n")
        recent = lines[-20:] if len(lines) > 20 else lines

        service = get_service()
        extracted = 0

        for line in recent:
            try:
                entry = json.loads(line)
                message = entry.get("message", "")
                if isinstance(message, dict):
                    message = message.get("text", "") or message.get("content", "")
                if not isinstance(message, str):
                    continue

                # Look for explicit knowledge statements
                # Pattern: "X is Y", "X uses Y", "X has Y", etc.
                text = message.strip()
                lower = text.lower()

                # Skip if too short or too long
                if len(text) < 10 or len(text) > 200:
                    continue

                # Look for common knowledge patterns in user statements
                if entry.get("type") == "user":
                    patterns = [
                        (" is a ", "is a"),
                        (" is an ", "is an"),
                        (" uses ", "uses"),
                        (" prefers ", "prefers"),
                        (" requires ", "requires"),
                        (" has ", "has"),
                    ]

                    for pattern, predicate in patterns:
                        if pattern in lower:
                            parts = text.split(pattern, 1)
                            if len(parts) == 2:
                                subject = parts[0].strip()
                                obj = parts[1].strip().rstrip(".")
                                if subject and obj and len(subject) < 50 and len(obj) < 100:
                                    service.add(
                                        subject=subject,
                                        predicate=predicate,
                                        obj=obj,
                                        source="session-hook",
                                        confidence=0.7,
                                    )
                                    extracted += 1
                            break

            except json.JSONDecodeError:
                continue

        if extracted > 0:
            print(json.dumps({"knowledge_extracted": extracted}))

    except (json.JSONDecodeError, KeyError):
        pass
