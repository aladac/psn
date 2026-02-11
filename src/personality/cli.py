"""CLI entry point for personality."""

import sys
from pathlib import Path

import click
from rich.console import Console

from personality import __version__
from personality.config import (
    DEFAULT_VOICE_DIR,
    get_cart_identity,
    get_cart_voice,
    list_carts,
    load_cart,
)
from personality.speak import Speak

console = Console()

DEFAULT_CART = "bt7274"


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Personality engine CLI."""
    if version:
        console.print(f"psn v{__version__}")
        return

    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@main.command()
@click.argument("text", required=False)
@click.option("-c", "--cart", default=DEFAULT_CART, help="Personality cart name.")
@click.option("-v", "--voice", help="Override voice model name.")
@click.option("-d", "--voice-dir", type=click.Path(exists=True), help="Voice models directory.")
@click.option("-o", "--output", type=click.Path(), help="Output WAV file instead of playing.")
@click.option("-i", "--input", "input_file", type=click.Path(exists=True), help="Read text from file.")
def speak(
    text: str | None,
    cart: str,
    voice: str | None,
    voice_dir: str | None,
    output: str | None,
    input_file: str | None,
) -> None:
    """Speak text using a personality cart.

    Examples:
        psn speak "Trust me, Pilot."
        psn speak -c GLADOS "The cake is a lie."
        echo "Hello" | psn speak
    """
    content = _resolve_text(text, input_file)
    if not content:
        console.print("[red]Error: No text provided.[/red]")
        console.print("[dim]Use argument, --input, or pipe from stdin.[/dim]")
        sys.exit(1)

    # Load cart and resolve voice
    cart_data = load_cart(cart)
    if not cart_data:
        console.print(f"[red]Cart not found:[/red] {cart}")
        console.print(f"[dim]Available: {', '.join(list_carts())}[/dim]")
        sys.exit(1)

    voice_name = voice or get_cart_voice(cart_data) or cart
    voice_path = Path(voice_dir) if voice_dir else DEFAULT_VOICE_DIR
    speaker = Speak(voice_path)

    try:
        if output:
            speaker.save(content, voice_name, Path(output))
            console.print(f"[green]Audio saved:[/green] {output}")
        else:
            speaker.say(content, voice_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]Playback error:[/red] {e}")
        sys.exit(1)


@main.command()
def carts() -> None:
    """List available personality carts."""
    from rich.table import Table

    cart_names = list_carts()
    if not cart_names:
        console.print("[yellow]No carts found.[/yellow]")
        console.print("[dim]Add carts to ~/.config/personality/carts/[/dim]")
        return

    table = Table(title="Available Carts", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Identity", style="white")
    table.add_column("Voice", style="dim")

    for name in sorted(cart_names):
        cart_data = load_cart(name)
        if cart_data:
            identity = get_cart_identity(cart_data)
            display_name = identity.get("name", name)
            voice = get_cart_voice(cart_data) or "[dim]default[/dim]"
            table.add_row(name, display_name, voice)

    console.print(table)


@main.command()
@click.option("-d", "--voice-dir", type=click.Path(exists=True), help="Voice models directory.")
def voices(voice_dir: str | None) -> None:
    """List available voice models."""
    from rich.table import Table

    voice_path = Path(voice_dir) if voice_dir else DEFAULT_VOICE_DIR

    if not voice_path.exists():
        console.print(f"[yellow]Voice directory not found:[/yellow] {voice_path}")
        return

    table = Table(title="Available Voices", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Model", style="dim")

    found = False
    for onnx_file in voice_path.glob("*.onnx"):
        config_file = onnx_file.with_suffix(".onnx.json")
        if config_file.exists():
            found = True
            table.add_row(onnx_file.stem, str(onnx_file.name))

    if found:
        console.print(table)
    else:
        console.print(f"[yellow]No voice models found in:[/yellow] {voice_path}")

    console.print(f"\n[dim]Voice directory: {voice_path}[/dim]")


@main.command()
@click.option("-c", "--cart", default=DEFAULT_CART, help="Active cart name.", envvar="PERSONALITY_CART")
def mcp(cart: str) -> None:
    """Start MCP server for Claude Code integration.

    Run as stdio transport for Claude Code plugin.

    Examples:
        psn mcp
        PERSONALITY_CART=glados psn mcp
    """
    import os

    # Set cart in environment for MCP server
    os.environ["PERSONALITY_CART"] = cart

    from personality.mcp import run_server

    run_server()


@main.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing commands.")
def install(force: bool) -> None:
    """Install Claude Code slash commands to ~/.claude/commands/psn/.

    Installs /psn:speak, /psn:cart, /psn:carts, /psn:voices, /psn:status commands.
    """
    from importlib.resources import files

    target_dir = Path.home() / ".claude" / "commands" / "psn"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Get commands from package
    commands_path = files("personality") / "commands"

    installed = []
    skipped = []

    for cmd_file in commands_path.iterdir():
        if cmd_file.name.endswith(".md"):
            target_file = target_dir / cmd_file.name
            if target_file.exists() and not force:
                skipped.append(cmd_file.name)
                continue

            target_file.write_text(cmd_file.read_text())
            installed.append(cmd_file.name)

    if installed:
        console.print(f"[green]Installed:[/green] {', '.join(installed)}")
    if skipped:
        console.print(f"[yellow]Skipped (use -f to overwrite):[/yellow] {', '.join(skipped)}")

    console.print(f"\n[dim]Commands installed to: {target_dir}[/dim]")


@main.command()
def uninstall() -> None:
    """Remove Claude Code slash commands from ~/.claude/commands/psn/."""
    import shutil

    target_dir = Path.home() / ".claude" / "commands" / "psn"

    if not target_dir.exists():
        console.print("[yellow]No commands installed.[/yellow]")
        return

    shutil.rmtree(target_dir)
    console.print("[green]Removed:[/green] ~/.claude/commands/psn/")


# Hook command group for Claude Code lifecycle events
@main.group()
def hook() -> None:
    """Claude Code hook commands for lifecycle events.

    These commands are invoked by Claude Code hooks (settings.json).
    They read JSON from stdin and output JSON to stdout.
    """


@hook.command("session-start")
@click.option("-c", "--cart", default=DEFAULT_CART, envvar="PERSONALITY_CART")
def hook_session_start(cart: str) -> None:
    """Handle session start: greet and load context."""
    from personality.hooks import session_start

    result = session_start(cart)
    click.echo(result.to_json())


@hook.command("session-end")
@click.option("-c", "--cart", default=DEFAULT_CART, envvar="PERSONALITY_CART")
def hook_session_end(cart: str) -> None:
    """Handle session end: consolidate memories and farewell."""
    from personality.hooks import session_end

    result = session_end(cart)
    click.echo(result.to_json())


@hook.command("stop")
@click.option("-c", "--cart", default=DEFAULT_CART, envvar="PERSONALITY_CART")
def hook_stop(cart: str) -> None:
    """Handle stop event: speak on end_turn only."""
    from personality.hooks import stop

    result = stop(cart)
    click.echo(result.to_json())


@hook.command("notify")
@click.option("-c", "--cart", default=DEFAULT_CART, envvar="PERSONALITY_CART")
@click.option("-m", "--message", help="Notification message to speak.")
def hook_notify(cart: str, message: str | None) -> None:
    """Handle notification: speak the message."""
    from personality.hooks import notify

    result = notify(cart, message)
    click.echo(result.to_json())


@main.command()
@click.option("--force", "-f", is_flag=True, help="Re-index all files.")
@click.option("--status", "-s", is_flag=True, help="Show index status.")
@click.argument("path", required=False, type=click.Path(exists=True))
def index(force: bool, status: bool, path: str | None) -> None:
    """Index a project for semantic code search.

    Examples:
        psn index              # Index current directory
        psn index --force      # Re-index all files
        psn index --status     # Show index status
        psn index /path/to/project
    """
    from personality.index import get_indexer

    project_path = Path(path) if path else Path.cwd()
    indexer = get_indexer(project_path)

    if status:
        info = indexer.status()
        console.print(f"[cyan]Project:[/cyan] {info['project_path']}")
        console.print(f"[cyan]Index:[/cyan] {info['db_path']}")
        console.print(f"[cyan]Files:[/cyan] {info['file_count']}")
        console.print(f"[cyan]Chunks:[/cyan] {info['chunk_count']}")
        console.print(f"[cyan]Summary:[/cyan] {'Yes' if info['has_summary'] else 'No'}")
        indexer.close()
        return

    console.print(f"[cyan]Indexing:[/cyan] {project_path}")
    stats = indexer.index(force=force)
    indexer.close()

    console.print(f"[green]Files indexed:[/green] {stats['files_indexed']}")
    console.print(f"[dim]Chunks created:[/dim] {stats['chunks_created']}")
    if stats["files_skipped"]:
        console.print(f"[dim]Files skipped (unchanged):[/dim] {stats['files_skipped']}")


@main.group()
def projects() -> None:
    """Manage indexed projects."""


@projects.command("list")
def projects_list() -> None:
    """List all indexed projects."""
    from rich.table import Table

    from personality.index import list_indexed_projects

    registry = list_indexed_projects()
    if not registry:
        console.print("[yellow]No projects indexed.[/yellow]")
        console.print("[dim]Run 'psn index' in a project directory.[/dim]")
        return

    table = Table(title="Indexed Projects", show_header=True)
    table.add_column("Project", style="cyan")
    table.add_column("Index DB", style="dim")

    for project_path, db_path in registry.items():
        table.add_row(project_path, Path(db_path).name)

    console.print(table)


@projects.command("rm")
@click.argument("path")
def projects_rm(path: str) -> None:
    """Remove a project index."""
    import json

    from personality.index.indexer import REGISTRY_FILE

    if not REGISTRY_FILE.exists():
        console.print("[yellow]No projects indexed.[/yellow]")
        return

    registry = json.loads(REGISTRY_FILE.read_text())

    if path not in registry:
        console.print(f"[red]Project not found:[/red] {path}")
        return

    db_path = Path(registry[path])
    if db_path.exists():
        db_path.unlink()
        console.print(f"[green]Removed index:[/green] {db_path}")

    del registry[path]
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2))
    console.print(f"[green]Unregistered:[/green] {path}")


@main.group()
def cart() -> None:
    """Manage portable carts (.pcart format)."""


@cart.command("export")
@click.argument("name")
@click.option("-o", "--output", help="Output path", required=True)
@click.option("--zip", "as_zip", is_flag=True, help="Export as ZIP archive")
@click.option("--no-voice", is_flag=True, help="Exclude voice model")
@click.option("--no-memories", is_flag=True, help="Exclude memories")
def cart_export(name: str, output: str, as_zip: bool, no_voice: bool, no_memories: bool) -> None:
    """Export a cart to portable format."""
    from personality.cart import PortableCart

    output_path = Path(output)
    if as_zip and not output_path.suffix:
        output_path = output_path.with_suffix(".zip")

    try:
        pcart = PortableCart.export(
            name,
            output_path,
            include_voice=not no_voice,
            include_memories=not no_memories,
            as_zip=as_zip,
        )
        console.print(f"[green]Exported:[/green] {output_path}")

        manifest = pcart.manifest
        console.print(f"[dim]Cart:[/dim] {manifest.cart_name}")
        console.print(f"[dim]Components:[/dim] {', '.join(manifest.components.keys())}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None


@cart.command("import")
@click.argument("path")
@click.option(
    "--mode",
    type=click.Choice(["safe", "override", "merge", "dry_run"]),
    default="safe",
    help="Import mode",
)
@click.option("--name", help="Override cart name")
def cart_import(path: str, mode: str, name: str | None) -> None:
    """Import a portable cart."""
    from personality.cart import InstallMode, PortableCart

    input_path = Path(path)
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise SystemExit(1)

    try:
        pcart = PortableCart.load(input_path)

        # Verify first
        verification = pcart.verify()
        if any(v != "valid" for v in verification.values()):
            console.print("[yellow]Warning: Some files failed verification[/yellow]")
            for filename, status in verification.items():
                if status != "valid":
                    console.print(f"  [red]{filename}:[/red] {status}")

        install_mode = InstallMode(mode)
        stats = pcart.install(mode=install_mode, target_name=name)

        console.print(f"[green]Installed:[/green] {stats['cart_name']}")
        for action in stats["actions"]:
            console.print(f"  [dim]{action}[/dim]")

        pcart.cleanup()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None


@cart.command("verify")
@click.argument("path")
def cart_verify(path: str) -> None:
    """Verify a portable cart's integrity."""
    from personality.cart import PortableCart

    input_path = Path(path)
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise SystemExit(1)

    pcart = PortableCart.load(input_path)
    results = pcart.verify()
    pcart.cleanup()

    all_valid = all(v == "valid" for v in results.values())
    if all_valid:
        console.print("[green]All files verified.[/green]")
    else:
        console.print("[red]Verification failed:[/red]")

    for filename, status in results.items():
        color = "green" if status == "valid" else "red"
        console.print(f"  [{color}]{filename}:[/{color}] {status}")


# Docs command group for document indexing
@main.group()
def docs() -> None:
    """Index and search markdown documentation."""


@docs.command("index")
@click.option("--force", "-f", is_flag=True, help="Re-index all files.")
@click.option("--path", "-p", type=click.Path(exists=True), help="Docs path.")
def docs_index(force: bool, path: str | None) -> None:
    """Index markdown documentation for semantic search.

    Examples:
        psn docs index              # Index ~/Projects/docs
        psn docs index --force      # Re-index all files
        psn docs index -p ./docs    # Index specific directory
    """
    from personality.docs import get_doc_indexer

    docs_path = Path(path) if path else Path.home() / "Projects" / "docs"

    if not docs_path.exists():
        console.print(f"[red]Error:[/red] Path not found: {docs_path}")
        raise SystemExit(1)

    console.print(f"[cyan]Indexing:[/cyan] {docs_path}")
    indexer = get_doc_indexer(docs_path)
    stats = indexer.index(force=force)
    indexer.close()

    console.print(f"[green]Files indexed:[/green] {stats['files_indexed']}")
    console.print(f"[dim]Chunks created:[/dim] {stats['chunks_created']}")
    if stats["files_skipped"]:
        console.print(f"[dim]Files skipped (unchanged):[/dim] {stats['files_skipped']}")


@docs.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Max results.")
@click.option("--path", "-p", type=click.Path(exists=True), help="Docs path.")
def docs_search(query: str, limit: int, path: str | None) -> None:
    """Search indexed documentation.

    Examples:
        psn docs search "MCP tools"
        psn docs search "authentication" --limit 10
    """
    from personality.docs import get_doc_indexer

    docs_path = Path(path) if path else Path.home() / "Projects" / "docs"
    indexer = get_doc_indexer(docs_path)
    results = indexer.search(query, k=limit)
    indexer.close()

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    for r in results:
        title = r.title or r.file_path
        console.print(f"[cyan]{title}[/cyan] (score: {r.score:.2f})")
        if r.heading:
            console.print(f"  [dim]## {r.heading}[/dim]")
        preview = r.content[:150].replace("\n", " ")
        console.print(f"  {preview}...")
        if r.source_url:
            console.print(f"  [dim]Source: {r.source_url}[/dim]")
        console.print()


@docs.command("list")
@click.option("--source", "-s", help="Filter by source URL pattern.")
@click.option("--path", "-p", type=click.Path(exists=True), help="Docs path.")
def docs_list(source: str | None, path: str | None) -> None:
    """List indexed documents.

    Examples:
        psn docs list
        psn docs list --source anthropic
    """
    from rich.table import Table

    from personality.docs import get_doc_indexer

    docs_path = Path(path) if path else Path.home() / "Projects" / "docs"
    indexer = get_doc_indexer(docs_path)
    documents = indexer.list_sources()
    indexer.close()

    if source:
        documents = [d for d in documents if source in (d.get("source_url") or "")]

    if not documents:
        console.print("[yellow]No documents indexed.[/yellow]")
        return

    table = Table(title="Indexed Documents", show_header=True)
    table.add_column("Title", style="cyan", max_width=40)
    table.add_column("Path", style="dim", max_width=30)
    table.add_column("Source", style="white", max_width=40)

    for doc in documents:
        title = doc.get("title") or ""
        doc_path = doc.get("path") or ""
        source_url = doc.get("source_url") or "[dim]local[/dim]"
        table.add_row(title[:40], doc_path[:30], source_url[:40])

    console.print(table)


@docs.command("status")
@click.option("--path", "-p", type=click.Path(exists=True), help="Docs path.")
def docs_status(path: str | None) -> None:
    """Show index status.

    Examples:
        psn docs status
    """
    from personality.docs import get_doc_indexer

    docs_path = Path(path) if path else Path.home() / "Projects" / "docs"
    indexer = get_doc_indexer(docs_path)
    info = indexer.status()
    indexer.close()

    console.print(f"[cyan]Docs Path:[/cyan] {info['docs_path']}")
    console.print(f"[cyan]Index:[/cyan] {info['db_path']}")
    console.print(f"[cyan]Documents:[/cyan] {info['document_count']}")
    console.print(f"[cyan]Chunks:[/cyan] {info['chunk_count']}")


@main.command()
def storage() -> None:
    """Show storage breakdown for all personality databases."""
    from rich.table import Table

    from personality.config import CONFIG_DIR

    def _format_size(size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"

    def _count_db_records(db_path: Path, table: str) -> int | None:
        """Count records in a SQLite table."""
        import sqlite3

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return None

    def _dir_stats(dir_path: Path, pattern: str = "*") -> tuple[int, int]:
        """Get total size and file count for a directory pattern."""
        if not dir_path.exists():
            return 0, 0
        files = list(dir_path.glob(pattern))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        return total_size, len(files)

    # Gather stats for each category
    categories = []

    # Carts (YAML configs)
    carts_dir = CONFIG_DIR / "carts"
    size, count = _dir_stats(carts_dir, "*.yml")
    categories.append(("Carts", size, f"{count} carts", str(carts_dir)))

    # Memory databases
    memory_dir = CONFIG_DIR / "memory"
    size, count = _dir_stats(memory_dir, "*.db")
    # Get record count from active cart db
    memory_records = None
    for db in memory_dir.glob("*.db"):
        records = _count_db_records(db, "memories")
        if records is not None:
            memory_records = (memory_records or 0) + records
    details = f"{memory_records} memories" if memory_records else f"{count} DBs"
    categories.append(("Memory", size, details, str(memory_dir)))

    # Docs index
    docs_dir = CONFIG_DIR / "docs"
    size, count = _dir_stats(docs_dir, "*.db")
    docs_chunks = None
    for db in docs_dir.glob("*.db"):
        chunks = _count_db_records(db, "doc_chunks")
        if chunks is not None:
            docs_chunks = (docs_chunks or 0) + chunks
    details = f"{docs_chunks} chunks" if docs_chunks else f"{count} DBs"
    categories.append(("Docs Index", size, details, str(docs_dir)))

    # Project indexes
    index_dir = CONFIG_DIR / "index"
    size, count = _dir_stats(index_dir, "*.db")
    categories.append(("Project Index", size, f"{count} projects", str(index_dir)))

    # Voice models
    voices_dir = CONFIG_DIR / "voices"
    size, count = _dir_stats(voices_dir, "*.onnx")
    categories.append(("Voices", size, f"{count} models", str(voices_dir)))

    # Build table
    table = Table(title="Personality Storage", show_header=True)
    table.add_column("Category", style="cyan")
    table.add_column("Size", style="white", justify="right")
    table.add_column("Contents", style="dim")

    total_size = 0
    for name, size, details, _ in categories:
        total_size += size
        table.add_row(name, _format_size(size), details)

    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold]{_format_size(total_size)}[/bold]", "")

    console.print(table)
    console.print(f"\n[dim]Config directory: {CONFIG_DIR}[/dim]")


# Diagnostics command group
@main.group()
def diag() -> None:
    """Diagnostic tools for debugging and inspection."""


@diag.command("memory")
@click.option("-c", "--cart", default=DEFAULT_CART, envvar="PERSONALITY_CART")
@click.option("-s", "--subject", help="Filter by subject prefix.")
@click.option("--stats", is_flag=True, help="Show statistics only.")
@click.option("--duplicates", is_flag=True, help="Find potential duplicates.")
def diag_memory(cart: str, subject: str | None, stats: bool, duplicates: bool) -> None:
    """Browse and inspect memories."""
    from rich.table import Table

    from personality.diagnostics import find_similar_memories, list_memories, memory_stats

    if stats:
        info = memory_stats(cart)
        console.print(f"[cyan]Total memories:[/cyan] {info['total']}")
        console.print(f"[cyan]Database:[/cyan] {info['db_path']}")
        console.print("\n[cyan]By prefix:[/cyan]")
        for prefix, count in sorted(info["by_prefix"].items()):
            console.print(f"  {prefix}: {count}")
        return

    if duplicates:
        similar = find_similar_memories(cart, threshold=0.7)
        if not similar:
            console.print("[green]No potential duplicates found.[/green]")
            return
        console.print(f"[yellow]Found {len(similar)} potential duplicates:[/yellow]\n")
        for m1, m2, score in similar[:10]:
            console.print(f"[cyan]{m1.subject}[/cyan] (id={m1.id}) <-> [cyan]{m2.subject}[/cyan] (id={m2.id})")
            console.print(f"  Similarity: {score:.0%}")
            console.print(f"  [dim]{m1.content[:80]}...[/dim]\n")
        return

    memories = list_memories(cart, subject)
    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return

    table = Table(title=f"Memories ({cart})", show_header=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Subject", style="cyan", width=25)
    table.add_column("Content", style="white", max_width=50)

    for mem in memories:
        content_preview = mem.content[:100].replace("\n", " ")
        table.add_row(str(mem.id), mem.subject, content_preview)

    console.print(table)


@diag.command("index")
@click.option("--orphans", is_flag=True, help="Show orphaned indexes (missing projects).")
@click.option("--stale", type=int, help="Show indexes older than N days.")
@click.option("--cleanup", is_flag=True, help="Remove orphaned indexes.")
def diag_index(orphans: bool, stale: int | None, cleanup: bool) -> None:
    """Check project index health."""
    from rich.table import Table

    from personality.diagnostics import (
        cleanup_orphaned_indexes,
        find_orphaned_indexes,
        find_stale_indexes,
        list_project_indexes,
    )

    if cleanup:
        removed = cleanup_orphaned_indexes()
        if removed:
            console.print(f"[green]Removed {len(removed)} orphaned indexes:[/green]")
            for path in removed:
                console.print(f"  [dim]{path}[/dim]")
        else:
            console.print("[green]No orphaned indexes to clean.[/green]")
        return

    if orphans:
        orphaned = find_orphaned_indexes()
        if not orphaned:
            console.print("[green]No orphaned indexes found.[/green]")
            return
        console.print(f"[yellow]Found {len(orphaned)} orphaned indexes:[/yellow]")
        for idx in orphaned:
            console.print(f"  [red]{idx.project_path}[/red]")
            console.print(f"    [dim]DB: {idx.db_path}[/dim]")
        console.print("\n[dim]Run 'psn diag index --cleanup' to remove.[/dim]")
        return

    if stale:
        from datetime import datetime

        stale_indexes = find_stale_indexes(stale)
        if not stale_indexes:
            console.print(f"[green]No indexes older than {stale} days.[/green]")
            return
        console.print(f"[yellow]Found {len(stale_indexes)} stale indexes:[/yellow]")
        for idx in stale_indexes:
            age = (datetime.now() - idx.last_modified).days
            console.print(f"  {idx.project_path} ({age} days old)")
        return

    # Default: show all indexes

    indexes = list_project_indexes()
    if not indexes:
        console.print("[yellow]No project indexes found.[/yellow]")
        return

    table = Table(title="Project Indexes", show_header=True)
    table.add_column("Project", style="cyan", max_width=40)
    table.add_column("Files", justify="right")
    table.add_column("Chunks", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Status", style="dim")

    for idx in sorted(indexes, key=lambda x: x.last_modified, reverse=True):
        size_mb = idx.db_size / (1024 * 1024)
        status = "[green]OK[/green]" if idx.exists and Path(idx.project_path).exists() else "[red]orphan[/red]"
        table.add_row(
            idx.project_path[-40:],
            str(idx.file_count),
            str(idx.chunk_count),
            f"{size_mb:.1f} MB",
            status,
        )

    console.print(table)


@diag.command("logs")
@click.option("-n", "--lines", default=20, help="Number of lines to show.")
@click.option("-e", "--event", help="Filter by event type.")
@click.option("--stats", is_flag=True, help="Show log statistics.")
def diag_logs(lines: int, event: str | None, stats: bool) -> None:
    """View and analyze hooks log."""
    from rich.table import Table

    from personality.diagnostics import get_log_stats, tail_logs

    if stats:
        info = get_log_stats()
        if not info.get("exists"):
            console.print("[yellow]No log file found.[/yellow]")
            return
        console.print(f"[cyan]Log size:[/cyan] {info['size'] / 1024:.1f} KB")
        console.print(f"[cyan]Entries analyzed:[/cyan] {info['total_entries']}")
        console.print("\n[cyan]By event:[/cyan]")
        for evt, count in sorted(info["by_event"].items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {evt}: {count}")
        console.print("\n[cyan]By level:[/cyan]")
        for level, count in info["by_level"].items():
            color = "red" if level == "ERROR" else "yellow" if level == "WARNING" else "white"
            console.print(f"  [{color}]{level}[/{color}]: {count}")
        return

    entries = tail_logs(lines, event)
    if not entries:
        console.print("[yellow]No log entries found.[/yellow]")
        return

    table = Table(show_header=True, show_lines=False)
    table.add_column("Time", style="dim", width=19)
    table.add_column("Level", width=7)
    table.add_column("Event", style="cyan", width=15)
    table.add_column("Message", style="white")

    for entry in entries:
        level_color = "red" if entry.level == "ERROR" else "yellow" if entry.level == "WARNING" else "white"
        table.add_row(entry.timestamp, f"[{level_color}]{entry.level}[/{level_color}]", entry.event, entry.message[:60])

    console.print(table)


@diag.command("embeddings")
def diag_embeddings() -> None:
    """Test embedding system connectivity and performance."""
    from personality.diagnostics import test_embeddings

    console.print("[cyan]Testing embedding system...[/cyan]")
    result = test_embeddings()

    if result.available:
        console.print("[green]Status:[/green] Available")
        console.print(f"[cyan]Model:[/cyan] {result.model}")
        console.print(f"[cyan]Dimensions:[/cyan] {result.dimensions}")
        console.print(f"[cyan]Latency:[/cyan] {result.latency_ms} ms")
    else:
        console.print("[red]Status:[/red] Unavailable")
        console.print(f"[red]Error:[/red] {result.error}")


def _resolve_text(text: str | None, input_file: str | None) -> str:
    """Resolve text from argument, file, or stdin."""
    if text:
        return text
    if input_file:
        return Path(input_file).read_text().strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


if __name__ == "__main__":
    main()
