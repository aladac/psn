"""Persona CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from personality.services.training_parser import TrainingParser

app = typer.Typer(
    name="persona",
    help="Persona training file management",
    invoke_without_command=True,
)
console = Console()

# Default training directory relative to plugin
TRAINING_DIR = Path(__file__).parent.parent.parent.parent / "training"


def get_training_dir() -> Path:
    """Get the training directory path."""
    return TRAINING_DIR


@app.callback(invoke_without_command=True)
def persona_main(ctx: typer.Context) -> None:
    """Persona training file management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("list")
def list_personas(
    directory: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Training directory (default: plugin training/)",
    ),
) -> None:
    """List available training personas."""
    training_dir = directory or get_training_dir()

    if not training_dir.exists():
        console.print(f"[red]Training directory not found:[/red] {training_dir}")
        raise typer.Exit(1)

    parser = TrainingParser()
    files = parser.list_training_files(training_dir)

    if not files:
        console.print("[yellow]No training files found.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Training Personas")
    table.add_column("Tag", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Memories", justify="right")
    table.add_column("File")

    for file_path in files:
        try:
            doc = parser.parse_file(file_path)
            table.add_row(
                doc.tag or file_path.stem,
                doc.version or "-",
                str(doc.count),
                file_path.name,
            )
        except Exception as e:
            table.add_row(
                file_path.stem,
                "[red]ERROR[/red]",
                "-",
                f"{file_path.name} ({e})",
            )

    console.print(table)


@app.command("show")
def show_persona(
    name: str = typer.Argument(..., help="Persona name (tag or filename)"),
    directory: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Training directory (default: plugin training/)",
    ),
    subjects: bool = typer.Option(
        False,
        "--subjects",
        "-s",
        help="Show subject categories only",
    ),
) -> None:
    """Show persona details."""
    training_dir = directory or get_training_dir()
    parser = TrainingParser()

    # Find the file
    file_path = _find_persona_file(name, training_dir, parser)
    if not file_path:
        console.print(f"[red]Persona not found:[/red] {name}")
        raise typer.Exit(1)

    try:
        doc = parser.parse_file(file_path)
    except Exception as e:
        console.print(f"[red]Failed to parse:[/red] {e}")
        raise typer.Exit(1) from None

    # Header
    console.print(f"\n[bold cyan]{doc.tag or file_path.stem}[/bold cyan]", end="")
    if doc.version:
        console.print(f" [dim]v{doc.version}[/dim]")
    else:
        console.print()
    console.print(f"[dim]Source: {file_path}[/dim]\n")

    # Preferences
    if doc.preferences:
        console.print("[bold]Preferences:[/bold]")
        _print_dict(doc.preferences, indent=2)
        console.print()

    # Memories
    console.print(f"[bold]Memories:[/bold] {doc.count} total\n")

    if subjects:
        # Group by subject prefix
        categories: dict[str, int] = {}
        for mem in doc.memories:
            prefix = mem.subject.split(".")[0] if "." in mem.subject else mem.subject
            categories[prefix] = categories.get(prefix, 0) + 1

        for cat, count in sorted(categories.items()):
            console.print(f"  [cyan]{cat}[/cyan]: {count}")
    else:
        # Show all memories
        for mem in doc.memories:
            content_preview = mem.content[:80] + "..." if len(mem.content) > 80 else mem.content
            console.print(f"  [cyan]{mem.subject}[/cyan]")
            console.print(f"    {content_preview}")


@app.command("validate")
def validate_persona(
    name: str = typer.Argument(..., help="Persona name (tag or filename)"),
    directory: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Training directory (default: plugin training/)",
    ),
) -> None:
    """Validate a training file."""
    training_dir = directory or get_training_dir()
    parser = TrainingParser()

    # Find the file
    file_path = _find_persona_file(name, training_dir, parser)
    if not file_path:
        console.print(f"[red]Persona not found:[/red] {name}")
        raise typer.Exit(1)

    is_valid, message = parser.validate_file(file_path)

    if is_valid:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]Invalid:[/red] {message}")
        raise typer.Exit(1)


@app.command("validate-all")
def validate_all(
    directory: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Training directory (default: plugin training/)",
    ),
) -> None:
    """Validate all training files."""
    training_dir = directory or get_training_dir()
    parser = TrainingParser()
    files = parser.list_training_files(training_dir)

    if not files:
        console.print("[yellow]No training files found.[/yellow]")
        raise typer.Exit(0)

    errors = 0
    for file_path in files:
        is_valid, message = parser.validate_file(file_path)
        if is_valid:
            console.print(f"[green]OK[/green] {file_path.name}: {message}")
        else:
            console.print(f"[red]FAIL[/red] {file_path.name}: {message}")
            errors += 1

    console.print()
    if errors:
        console.print(f"[red]{errors} file(s) failed validation[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[green]All {len(files)} files valid[/green]")


def _find_persona_file(name: str, training_dir: Path, parser: TrainingParser) -> Path | None:
    """Find a persona file by name or tag."""
    # Try exact filename first
    for ext in (".yml", ".yaml", ".jsonld"):
        candidate = training_dir / f"{name}{ext}"
        if candidate.exists():
            return candidate

    # Try case-insensitive match
    name_lower = name.lower()
    for file_path in parser.list_training_files(training_dir):
        if file_path.stem.lower() == name_lower:
            return file_path

    # Try matching by tag
    for file_path in parser.list_training_files(training_dir):
        try:
            doc = parser.parse_file(file_path)
            if doc.tag.lower() == name_lower:
                return file_path
        except Exception:
            continue

    return None


def _print_dict(d: dict, indent: int = 0) -> None:
    """Pretty print a dictionary."""
    prefix = " " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            console.print(f"{prefix}[dim]{key}:[/dim]")
            _print_dict(value, indent + 2)
        else:
            console.print(f"{prefix}[dim]{key}:[/dim] {value}")
