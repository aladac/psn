"""MCP CLI commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="mcp",
    help="MCP server management",
    invoke_without_command=True,
)
console = Console()


@app.callback(invoke_without_command=True)
def mcp_main(ctx: typer.Context) -> None:
    """MCP server management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("serve")
def serve() -> None:
    """Run the MCP server (stdio transport)."""
    from personality.mcp import run_server

    asyncio.run(run_server())


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
