"""Config CLI commands."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from personality.config import (
    CONFIG_FILE,
    get_config,
    get_default_config_toml,
    init_config,
    reload_config,
)

app = typer.Typer(help="Configuration management")
console = Console()

# =============================================================================
# Logging Configuration
# =============================================================================

LOGGING_CONFIG_FILE = Path.home() / ".config" / "psn" / "logging.toml"


def get_default_logging_toml() -> str:
    """Generate default logging.toml content."""
    return '''\
# PSN Hook Logging Configuration
# Location: ~/.config/psn/logging.toml

[truncation]
# Maximum length for string values (except preserved fields)
max_length = 50

# Fields that should never be truncated (exact match, case-insensitive)
preserve_fields = [
    "path",
    "file_path",
    "cwd",
    "transcript_path",
    "file",
    "directory",
]

# Field name suffixes that should never be truncated
preserve_suffixes = [
    "_path",
    "_dir",
]
'''


def init_logging_config(overwrite: bool = False) -> tuple[bool, str]:
    """Initialize logging config file with defaults."""
    LOGGING_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LOGGING_CONFIG_FILE.exists() and not overwrite:
        return False, f"Logging config already exists at {LOGGING_CONFIG_FILE}"

    LOGGING_CONFIG_FILE.write_text(get_default_logging_toml())
    return True, f"Created logging config at {LOGGING_CONFIG_FILE}"


# Logging subcommand group
logging_app = typer.Typer(help="Hook logging configuration")
app.add_typer(logging_app, name="logging")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize config file with defaults."""
    created, message = init_config(overwrite=force)
    if created:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[yellow]{message}[/yellow]")
        console.print("Use --force to overwrite.")


@app.command()
def show() -> None:
    """Show current configuration."""
    if not CONFIG_FILE.exists():
        console.print(f"[yellow]No config file at {CONFIG_FILE}[/yellow]")
        console.print("Using defaults. Run 'psn config init' to create config file.")
        console.print()

    cfg = get_config()

    table = Table(title="PSN Configuration", show_header=True)
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="green")
    table.add_column("Value", style="white")

    # Remote
    table.add_row("remote", "host", cfg.remote.host)
    table.add_row("remote", "ssh_key", cfg.remote.ssh_key)

    # Postgres
    table.add_row("postgres", "host", cfg.postgres.host)
    table.add_row("postgres", "port", str(cfg.postgres.port))
    table.add_row("postgres", "database", cfg.postgres.database)
    table.add_row("postgres", "user", cfg.postgres.user)

    # Ollama
    table.add_row("ollama", "host", cfg.ollama.host)
    table.add_row("ollama", "port", str(cfg.ollama.port))
    table.add_row("ollama", "embedding_model", cfg.ollama.embedding_model)
    table.add_row("ollama", "(url)", cfg.ollama.url)

    # TTS
    table.add_row("tts", "voice", cfg.tts.voice)
    table.add_row("tts", "rate", str(cfg.tts.rate))

    # Paths
    table.add_row("paths", "homebrew", cfg.paths.homebrew)
    table.add_row("paths", "data_dir", cfg.paths.data_dir)

    console.print(table)

    if CONFIG_FILE.exists():
        console.print(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@app.command()
def path() -> None:
    """Show config file path."""
    console.print(str(CONFIG_FILE))


@app.command()
def edit() -> None:
    """Open config file in editor."""
    if not CONFIG_FILE.exists():
        console.print("[yellow]Config file doesn't exist. Creating with defaults...[/yellow]")
        init_config()

    editor = subprocess.run(
        ["which", "code"],
        capture_output=True,
        text=True,
    )
    if editor.returncode == 0:
        subprocess.run(["code", str(CONFIG_FILE)])
    else:
        # Fall back to $EDITOR or vim
        import os
        editor_cmd = os.environ.get("EDITOR", "vim")
        subprocess.run([editor_cmd, str(CONFIG_FILE)])


@app.command()
def cat() -> None:
    """Print config file contents."""
    if not CONFIG_FILE.exists():
        console.print(f"[yellow]No config file at {CONFIG_FILE}[/yellow]")
        console.print("\n[dim]Default configuration:[/dim]\n")
        syntax = Syntax(get_default_config_toml(), "toml", theme="monokai")
        console.print(syntax)
        return

    content = CONFIG_FILE.read_text()
    syntax = Syntax(content, "toml", theme="monokai", line_numbers=True)
    console.print(syntax)


@app.command()
def defaults() -> None:
    """Print default configuration."""
    syntax = Syntax(get_default_config_toml(), "toml", theme="monokai")
    console.print(syntax)


@app.command()
def validate() -> None:
    """Validate config file syntax and values."""
    if not CONFIG_FILE.exists():
        console.print(f"[yellow]No config file at {CONFIG_FILE}[/yellow]")
        console.print("Using defaults (valid).")
        return

    try:
        reload_config()
        console.print("[green]Configuration is valid.[/green]")
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)


@app.command("get")
def get_value(
    key: str = typer.Argument(..., help="Config key (e.g., postgres.host, ollama.url)"),
) -> None:
    """Get a specific config value."""
    cfg = get_config()

    # Parse dotted key
    parts = key.split(".")
    value = cfg

    try:
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                console.print(f"[red]Unknown key: {key}[/red]")
                sys.exit(1)

        # Print raw value (useful for scripts)
        print(value)
    except Exception as e:
        console.print(f"[red]Error getting {key}: {e}[/red]")
        sys.exit(1)


# =============================================================================
# Logging Subcommands
# =============================================================================


@logging_app.command("init")
def logging_init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize logging config file with defaults."""
    created, message = init_logging_config(overwrite=force)
    if created:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[yellow]{message}[/yellow]")
        console.print("Use --force to overwrite.")


@logging_app.command("show")
def logging_show() -> None:
    """Show current logging configuration."""
    import tomllib

    if not LOGGING_CONFIG_FILE.exists():
        console.print(f"[yellow]No logging config at {LOGGING_CONFIG_FILE}[/yellow]")
        console.print("Using defaults. Run 'psn config logging init' to create.")
        console.print()
        # Show defaults
        max_len = 50
        preserve_fields = ["path", "file_path", "cwd", "transcript_path", "file", "directory"]
        preserve_suffixes = ["_path", "_dir"]
    else:
        try:
            with LOGGING_CONFIG_FILE.open("rb") as f:
                cfg = tomllib.load(f)
            t = cfg.get("truncation", {})
            max_len = t.get("max_length", 50)
            preserve_fields = t.get("preserve_fields", [])
            preserve_suffixes = t.get("preserve_suffixes", [])
        except Exception as e:
            console.print(f"[red]Error reading config: {e}[/red]")
            return

    table = Table(title="Hook Logging Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("max_length", str(max_len))
    table.add_row("preserve_fields", ", ".join(preserve_fields))
    table.add_row("preserve_suffixes", ", ".join(preserve_suffixes))

    console.print(table)

    if LOGGING_CONFIG_FILE.exists():
        console.print(f"\n[dim]Config file: {LOGGING_CONFIG_FILE}[/dim]")


@logging_app.command("cat")
def logging_cat() -> None:
    """Print logging config file contents."""
    if not LOGGING_CONFIG_FILE.exists():
        console.print(f"[yellow]No logging config at {LOGGING_CONFIG_FILE}[/yellow]")
        console.print("\n[dim]Default configuration:[/dim]\n")
        syntax = Syntax(get_default_logging_toml(), "toml", theme="monokai")
        console.print(syntax)
        return

    content = LOGGING_CONFIG_FILE.read_text()
    syntax = Syntax(content, "toml", theme="monokai", line_numbers=True)
    console.print(syntax)


@logging_app.command("edit")
def logging_edit() -> None:
    """Open logging config file in editor."""
    import os

    if not LOGGING_CONFIG_FILE.exists():
        console.print("[yellow]Logging config doesn't exist. Creating with defaults...[/yellow]")
        init_logging_config()

    editor = subprocess.run(["which", "code"], capture_output=True, text=True)
    if editor.returncode == 0:
        subprocess.run(["code", str(LOGGING_CONFIG_FILE)])
    else:
        editor_cmd = os.environ.get("EDITOR", "vim")
        subprocess.run([editor_cmd, str(LOGGING_CONFIG_FILE)])


@logging_app.command("path")
def logging_path() -> None:
    """Show logging config file path."""
    console.print(str(LOGGING_CONFIG_FILE))
