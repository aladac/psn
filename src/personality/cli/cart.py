"""Cart CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from personality.services.cart_registry import CartRegistry

app = typer.Typer(
    name="cart",
    help="Cartridge management",
    invoke_without_command=True,
)
console = Console()

# Default training directory
TRAINING_DIR = Path(__file__).parent.parent.parent.parent / "training"


def get_registry() -> CartRegistry:
    """Get the cart registry."""
    return CartRegistry()


@app.callback(invoke_without_command=True)
def cart_main(ctx: typer.Context) -> None:
    """Cartridge management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("list")
def list_carts() -> None:
    """List installed cartridges."""
    registry = get_registry()
    carts = registry.list_available()
    active_tag = registry.get_active_tag()

    if not carts:
        console.print("[yellow]No cartridges installed.[/yellow]")
        console.print("\nCreate one from training data:")
        console.print("  psn cart create <persona-name>")
        raise typer.Exit(0)

    table = Table(title="Installed Cartridges")
    table.add_column("", width=2)  # Active indicator
    table.add_column("Tag", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Memories", justify="right")
    table.add_column("File")

    for cart in carts:
        if "error" in cart:
            table.add_row(
                "",
                cart.get("tag", "?"),
                "[red]ERROR[/red]",
                "-",
                cart.get("filename", "?"),
            )
        else:
            is_active = cart.get("tag") == active_tag
            indicator = "[green]>[/green]" if is_active else ""
            table.add_row(
                indicator,
                cart.get("tag", "?"),
                cart.get("version", "-"),
                str(cart.get("memory_count", 0)),
                cart.get("filename", "?"),
            )

    console.print(table)

    if active_tag:
        console.print(f"\n[dim]Active:[/dim] [green]{active_tag}[/green]")


@app.command("create")
def create_cart(
    name: str = typer.Argument(..., help="Training persona name or path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing cart"),
) -> None:
    """Create a cartridge from training data."""
    registry = get_registry()

    # Find the training file
    training_path = _find_training_file(name)
    if not training_path:
        console.print(f"[red]Training file not found:[/red] {name}")
        console.print("\nAvailable training files:")
        for f in sorted(TRAINING_DIR.glob("*.yml")):
            console.print(f"  {f.stem}")
        raise typer.Exit(1)

    # Check if cart already exists
    expected_tag = training_path.stem.lower()
    cart_path = registry.carts_dir / f"{expected_tag}.pcart"
    if cart_path.exists() and not force:
        console.print(f"[yellow]Cart already exists:[/yellow] {cart_path}")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)

    try:
        cart = registry.create_from_training(training_path)
        console.print(f"[green]Created:[/green] {cart.path}")
        console.print(f"  Tag: {cart.tag}")
        console.print(f"  Version: {cart.manifest.version}")
        console.print(f"  Memories: {cart.memory_count}")
    except Exception as e:
        console.print(f"[red]Failed to create cart:[/red] {e}")
        raise typer.Exit(1) from None


@app.command("create-all")
def create_all_carts(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing carts"),
) -> None:
    """Create cartridges from all training files."""
    registry = get_registry()

    if not TRAINING_DIR.exists():
        console.print(f"[red]Training directory not found:[/red] {TRAINING_DIR}")
        raise typer.Exit(1)

    training_files = sorted(TRAINING_DIR.glob("*.yml"))
    if not training_files:
        console.print("[yellow]No training files found.[/yellow]")
        raise typer.Exit(0)

    created = 0
    skipped = 0
    failed = 0

    for training_path in training_files:
        expected_tag = training_path.stem.lower()
        cart_path = registry.carts_dir / f"{expected_tag}.pcart"

        if cart_path.exists() and not force:
            console.print(f"[dim]Skipped:[/dim] {expected_tag} (exists)")
            skipped += 1
            continue

        try:
            cart = registry.create_from_training(training_path)
            console.print(f"[green]Created:[/green] {cart.tag} ({cart.memory_count} memories)")
            created += 1
        except Exception as e:
            console.print(f"[red]Failed:[/red] {training_path.name}: {e}")
            failed += 1

    console.print(f"\n[bold]Summary:[/bold] {created} created, {skipped} skipped, {failed} failed")


@app.command("switch")
def switch_cart(
    name: str = typer.Argument(..., help="Cart tag to switch to"),
) -> None:
    """Switch active cartridge."""
    from personality.cli.tts import find_voice_path

    registry = get_registry()

    try:
        cart = registry.switch_to(name)
        console.print(f"[green]Switched to:[/green] {cart.tag}")
        if cart.preferences.identity.name:
            console.print(f"  Name: {cart.preferences.identity.name}")
        if cart.voice:
            voice_path = find_voice_path(cart.voice)
            if voice_path:
                console.print(f"  Voice: {cart.voice} [green]✓[/green]")
            else:
                console.print(f"  Voice: {cart.voice} [yellow](not installed)[/yellow]")
        if cart.preferences.tts.enabled:
            console.print("  TTS: [green]enabled[/green]")
    except FileNotFoundError:
        console.print(f"[red]Cart not found:[/red] {name}")
        console.print("\nAvailable carts:")
        for cart_info in registry.list_available():
            console.print(f"  {cart_info.get('tag', '?')}")
        raise typer.Exit(1) from None


@app.command("show")
def show_cart(
    name: str = typer.Argument(None, help="Cart tag (default: active cart)"),
    memories: bool = typer.Option(False, "--memories", "-m", help="Show all memories"),
) -> None:
    """Show cartridge details."""
    registry = get_registry()

    if name:
        try:
            cart = registry.load_by_tag(name)
        except FileNotFoundError:
            console.print(f"[red]Cart not found:[/red] {name}")
            raise typer.Exit(1) from None
    else:
        cart = registry.get_active()
        if not cart:
            console.print("[yellow]No active cart.[/yellow]")
            console.print("Use: psn cart switch <name>")
            raise typer.Exit(0)

    # Header
    console.print(f"\n[bold cyan]{cart.tag}[/bold cyan]", end="")
    if cart.manifest.version:
        console.print(f" [dim]v{cart.manifest.version}[/dim]")
    else:
        console.print()

    if cart.path:
        console.print(f"[dim]Path: {cart.path}[/dim]")

    # Identity
    console.print("\n[bold]Identity:[/bold]")
    identity = cart.preferences.identity
    if identity.name:
        console.print(f"  Name: {identity.name}")
    if identity.full_name:
        console.print(f"  Full Name: {identity.full_name}")
    if identity.type:
        console.print(f"  Type: {identity.type}")
    if identity.tagline:
        console.print(f"  Tagline: {identity.tagline}")

    # TTS
    if cart.preferences.tts.voice:
        console.print("\n[bold]TTS:[/bold]")
        console.print(f"  Voice: {cart.preferences.tts.voice}")
        console.print(f"  Enabled: {cart.preferences.tts.enabled}")

    # Memories
    console.print(f"\n[bold]Memories:[/bold] {cart.memory_count}")

    if memories:
        for mem in cart.persona.memories:
            content_preview = mem.content[:60] + "..." if len(mem.content) > 60 else mem.content
            console.print(f"  [cyan]{mem.subject}[/cyan]: {content_preview}")
    else:
        # Show subject categories
        categories: dict[str, int] = {}
        for mem in cart.persona.memories:
            prefix = mem.subject.split(".")[0] if "." in mem.subject else mem.subject
            categories[prefix] = categories.get(prefix, 0) + 1

        for cat, count in sorted(categories.items()):
            console.print(f"  {cat}: {count}")


@app.command("clear")
def clear_active() -> None:
    """Clear the active cartridge."""
    registry = get_registry()
    registry.clear_active()
    console.print("[green]Active cart cleared.[/green]")


def _find_training_file(name: str) -> Path | None:
    """Find a training file by name."""
    # Check if it's a path
    if "/" in name or name.endswith(".yml"):
        path = Path(name)
        if path.exists():
            return path
        return None

    # Try in training directory
    for ext in (".yml", ".yaml"):
        # Exact match
        path = TRAINING_DIR / f"{name}{ext}"
        if path.exists():
            return path

        # Case-insensitive match
        name_lower = name.lower()
        for f in TRAINING_DIR.glob(f"*{ext}"):
            if f.stem.lower() == name_lower:
                return f

    return None
