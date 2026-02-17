"""MCP CLI commands."""

import asyncio
import importlib.util
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="mcp",
    help="MCP server management",
    invoke_without_command=True,
)
console = Console()

# Server registry - maps names to their module paths
SERVERS_DIR = Path(__file__).parent.parent / "servers"
AVAILABLE_SERVERS = {
    "tts": SERVERS_DIR / "tts.py",
    "ollama": SERVERS_DIR / "ollama.py",
    "postgres": SERVERS_DIR / "postgres.py",
    "sqlite": SERVERS_DIR / "sqlite.py",
    "memory": SERVERS_DIR / "memory.py",
    "indexer": SERVERS_DIR / "indexer.py",
    "docker-local": SERVERS_DIR / "docker_local.py",
    "docker-remote": SERVERS_DIR / "docker_remote.py",
}


@app.callback(invoke_without_command=True)
def mcp_main(ctx: typer.Context) -> None:
    """MCP server management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("serve")
def serve() -> None:
    """Run the main persona MCP server (stdio transport)."""
    from personality.mcp import run_server

    asyncio.run(run_server())


def _run_server_module(server_path: Path) -> None:
    """Load and run an MCP server module."""
    spec = importlib.util.spec_from_file_location("server_module", server_path)
    if spec is None or spec.loader is None:
        console.print(f"[red]Error:[/red] Cannot load server from {server_path}")
        raise typer.Exit(1)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "main"):
        asyncio.run(module.main())
    else:
        console.print(f"[red]Error:[/red] Server module has no main() function")
        raise typer.Exit(1)


@app.command("tts")
def run_tts() -> None:
    """Run the TTS MCP server."""
    _run_server_module(AVAILABLE_SERVERS["tts"])


@app.command("ollama")
def run_ollama() -> None:
    """Run the Ollama MCP server."""
    _run_server_module(AVAILABLE_SERVERS["ollama"])


@app.command("postgres")
def run_postgres() -> None:
    """Run the PostgreSQL MCP server."""
    _run_server_module(AVAILABLE_SERVERS["postgres"])


@app.command("sqlite")
def run_sqlite() -> None:
    """Run the SQLite MCP server."""
    _run_server_module(AVAILABLE_SERVERS["sqlite"])


@app.command("memory")
def run_memory() -> None:
    """Run the Memory MCP server."""
    _run_server_module(AVAILABLE_SERVERS["memory"])


@app.command("indexer")
def run_indexer() -> None:
    """Run the Indexer MCP server."""
    _run_server_module(AVAILABLE_SERVERS["indexer"])


@app.command("docker-local")
def run_docker_local() -> None:
    """Run the Docker Local MCP server."""
    _run_server_module(AVAILABLE_SERVERS["docker-local"])


@app.command("docker-remote")
def run_docker_remote() -> None:
    """Run the Docker Remote MCP server."""
    _run_server_module(AVAILABLE_SERVERS["docker-remote"])


@app.command("resources")
def list_resources() -> None:
    """List available MCP resources."""
    from personality.mcp.server import list_resources as get_resources

    async def _list() -> None:
        resources = await get_resources()
        table = Table(title="MCP Resources")
        table.add_column("URI", style="cyan")
        table.add_column("Name")
        table.add_column("Description", style="dim")

        for r in resources:
            table.add_row(str(r.uri), r.name, r.description or "")

        console.print(table)

    asyncio.run(_list())


@app.command("read")
def read_resource(
    uri: str = typer.Argument(..., help="Resource URI to read"),
) -> None:
    """Read a specific MCP resource."""
    from personality.mcp.server import read_resource as _read

    async def _do_read() -> None:
        result = await _read(uri)
        for content in result:
            console.print(content.text)

    asyncio.run(_do_read())


@app.command("prompts")
def list_prompts_cmd() -> None:
    """List available MCP prompts."""
    from personality.mcp.server import list_prompts

    async def _list() -> None:
        prompts = await list_prompts()
        table = Table(title="MCP Prompts")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Arguments", style="dim")

        for p in prompts:
            args_str = ", ".join(f"{a.name}{'*' if a.required else ''}" for a in (p.arguments or []))
            table.add_row(p.name, p.description or "", args_str)

        console.print(table)
        console.print("\n[dim]* = required argument[/dim]")

    asyncio.run(_list())


@app.command("prompt")
def run_prompt(
    name: str = typer.Argument(..., help="Prompt name"),
    args: list[str] = typer.Argument(None, help="Arguments as key=value pairs"),
) -> None:
    """Execute an MCP prompt."""
    from personality.mcp.server import get_prompt

    # Parse key=value arguments
    arguments: dict[str, str] = {}
    for arg in args or []:
        if "=" in arg:
            key, value = arg.split("=", 1)
            arguments[key] = value

    async def _run() -> None:
        try:
            result = await get_prompt(name, arguments)
            console.print(f"[bold]{result.description}[/bold]\n")
            for msg in result.messages:
                console.print(f"[dim]{msg.role}:[/dim]")
                if hasattr(msg.content, "text"):
                    console.print(msg.content.text)
                else:
                    console.print(str(msg.content))
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    asyncio.run(_run())
