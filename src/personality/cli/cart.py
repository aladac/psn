"""Cart CLI commands."""

import json
import sys
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


@app.command("import-memories")
def import_memories(
    path: str = typer.Argument(None, help="Path to .pcart file (default: active cart)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without importing"),
    filter_prefix: str = typer.Option(None, "--filter", "-f", help="Only import subjects matching prefix"),
) -> None:
    """Import training memories from a pcart into the vector memory database."""
    import zipfile

    import psycopg
    import yaml
    from pgvector.psycopg import register_vector
    from sentence_transformers import SentenceTransformer

    from personality.config import get_config

    registry = get_registry()

    # Determine pcart path
    if path:
        pcart_path = Path(path)
        if not pcart_path.exists():
            # Try as tag name
            pcart_path = registry.carts_dir / f"{path}.pcart"
        if not pcart_path.exists():
            console.print(f"[red]Cart not found:[/red] {path}")
            raise typer.Exit(1)
    else:
        cart = registry.get_active()
        if not cart or not cart.path:
            console.print("[yellow]No active cart. Specify a path or tag.[/yellow]")
            raise typer.Exit(1)
        pcart_path = cart.path

    console.print(f"[dim]Source:[/dim] {pcart_path}")

    # Read pcart contents
    try:
        with zipfile.ZipFile(pcart_path, "r") as zf:
            if "persona.yml" not in zf.namelist():
                console.print("[red]Invalid pcart: missing persona.yml[/red]")
                raise typer.Exit(1)

            persona_yaml = zf.read("persona.yml").decode("utf-8")
            persona_data = yaml.safe_load(persona_yaml) or {}

            # Also read preferences if available
            prefs_data = {}
            if "preferences.yml" in zf.namelist():
                prefs_yaml = zf.read("preferences.yml").decode("utf-8")
                prefs_data = yaml.safe_load(prefs_yaml) or {}
    except zipfile.BadZipFile:
        console.print(f"[red]Invalid ZIP file:[/red] {pcart_path}")
        raise typer.Exit(1) from None

    tag = persona_data.get("tag", pcart_path.stem)
    version = str(persona_data.get("version", ""))
    memories = persona_data.get("memories", [])

    # Apply filter
    if filter_prefix:
        memories = [m for m in memories if m.get("subject", "").startswith(filter_prefix)]

    console.print(f"[dim]Cart:[/dim] {tag} v{version}")
    console.print(f"[dim]Memories:[/dim] {len(memories)}")

    if not memories:
        console.print("[yellow]No memories to import.[/yellow]")
        raise typer.Exit(0)

    if dry_run:
        console.print("\n[bold yellow]DRY RUN - No changes will be made[/bold yellow]\n")
        table = Table(title="Memories to Import")
        table.add_column("Subject", style="cyan")
        table.add_column("Content Preview")

        for mem in memories[:20]:  # Show first 20
            subject = mem.get("subject", "?")
            content = str(mem.get("content", ""))
            preview = content[:50] + "..." if len(content) > 50 else content
            table.add_row(subject, preview)

        if len(memories) > 20:
            table.add_row("...", f"[dim]and {len(memories) - 20} more[/dim]")

        console.print(table)
        raise typer.Exit(0)

    # Connect to database
    cfg = get_config().postgres
    try:
        conn = psycopg.connect(
            host=cfg.host,
            port=cfg.port,
            dbname=cfg.database,
            user=cfg.user,
        )
        register_vector(conn)
    except Exception as e:
        console.print(f"[red]Database connection failed:[/red] {e}")
        raise typer.Exit(1) from None

    # Ensure schema and get/create cart
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tag TEXT UNIQUE NOT NULL,
                version TEXT,
                name TEXT,
                type TEXT,
                tagline TEXT,
                source TEXT,
                pcart_path TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY,
                cart_id UUID REFERENCES carts(id) ON DELETE CASCADE,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Migration: add cart_id column if missing
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'memories' AND column_name = 'cart_id'
        """)
        if not cur.fetchone():
            console.print("[dim]Migrating: adding cart_id column...[/dim]")
            cur.execute("ALTER TABLE memories ADD COLUMN cart_id UUID REFERENCES carts(id) ON DELETE CASCADE")
            conn.commit()

        cur.execute(
            "CREATE INDEX IF NOT EXISTS memories_cart_id_idx ON memories (cart_id)"
        )
        conn.commit()

        # Get or create cart
        cur.execute("SELECT id FROM carts WHERE tag = %s", (tag,))
        row = cur.fetchone()
        if row:
            cart_id = str(row[0])
            console.print(f"[dim]Using existing cart:[/dim] {cart_id[:8]}...")
        else:
            from uuid import uuid4
            cart_id = str(uuid4())
            identity = prefs_data.get("identity", {})
            cur.execute(
                """
                INSERT INTO carts (id, tag, version, name, type, tagline, source, pcart_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cart_id,
                    tag,
                    version,
                    identity.get("name"),
                    identity.get("type"),
                    identity.get("tagline"),
                    identity.get("source"),
                    str(pcart_path),
                ),
            )
            conn.commit()
            console.print(f"[green]Registered cart:[/green] {cart_id[:8]}...")

    # Load embedding model
    console.print("[dim]Loading embedding model...[/dim]")
    try:
        ollama_cfg = get_config().ollama
        model = SentenceTransformer(ollama_cfg.embedding_model, trust_remote_code=True)
    except Exception as e:
        console.print(f"[red]Failed to load embedding model:[/red] {e}")
        raise typer.Exit(1) from None

    # Import memories
    imported = 0
    skipped = 0
    failed = 0

    with console.status("[bold green]Importing memories...") as status:
        for i, mem in enumerate(memories):
            subject = mem.get("subject", "")
            content = mem.get("content", "")

            if isinstance(content, list):
                content = ", ".join(str(x) for x in content)
            content = str(content)

            if not subject or not content:
                skipped += 1
                continue

            status.update(f"[bold green]Importing {i + 1}/{len(memories)}: {subject[:30]}...")

            try:
                # Check for duplicate
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM memories WHERE cart_id = %s AND subject = %s AND content = %s",
                        (cart_id, subject, content),
                    )
                    if cur.fetchone():
                        skipped += 1
                        continue

                # Generate embedding
                embedding = model.encode(content, convert_to_numpy=True).tolist()

                # Insert memory
                from uuid import uuid4
                memory_id = str(uuid4())
                metadata = {"source": "pcart-import", "original_index": i}

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO memories (id, cart_id, subject, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (memory_id, cart_id, subject, content, embedding, json.dumps(metadata)),
                    )
                conn.commit()
                imported += 1

            except Exception as e:
                console.print(f"[red]Failed:[/red] {subject}: {e}")
                failed += 1

    conn.close()

    console.print(f"\n[bold]Import complete:[/bold]")
    console.print(f"  [green]Imported:[/green] {imported}")
    console.print(f"  [yellow]Skipped:[/yellow] {skipped}")
    if failed:
        console.print(f"  [red]Failed:[/red] {failed}")


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


# Project to persona mapping (can be extended)
PROJECT_PERSONA_MAP = {
    "psn": "bt7274",
    "personality": "bt7274",
    "claude": "bt7274",
}


@app.command("hook-session-start")
def hook_session_start() -> None:
    """SessionStart hook: auto-switch persona based on project directory."""
    try:
        data = json.load(sys.stdin)
        cwd = data.get("cwd", "")

        if not cwd:
            return

        cwd_path = Path(cwd)
        project_name = cwd_path.name.lower()

        # Check if we have a mapping for this project
        persona = PROJECT_PERSONA_MAP.get(project_name)

        if persona:
            registry = get_registry()
            current = registry.get_active()

            # Only switch if different from current
            if current is None or current.tag.lower() != persona.lower():
                try:
                    cart = registry.switch_to(persona)
                    print(json.dumps({"persona_switched": cart.tag}))
                except FileNotFoundError:
                    pass  # Persona not available

    except (json.JSONDecodeError, KeyError):
        pass
