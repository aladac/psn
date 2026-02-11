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
