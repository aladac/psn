"""Decision CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from personality.schemas.decision import DecisionStatus
from personality.services.decision import DecisionService

app = typer.Typer(
    name="decision",
    help="Decision tracking (ADR-style)",
    invoke_without_command=True,
)
console = Console()


def get_service() -> DecisionService:
    """Get the decision service."""
    return DecisionService()


@app.callback(invoke_without_command=True)
def decision_main(ctx: typer.Context) -> None:
    """Decision tracking (ADR-style)."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("record")
def record_decision(
    title: str = typer.Argument(..., help="Decision title"),
    context: str = typer.Option("", "--context", "-c", help="Context and background"),
    decision: str = typer.Option("", "--decision", "-d", help="The decision made"),
    rationale: str = typer.Option("", "--rationale", "-r", help="Why this decision"),
    alternatives: list[str] = typer.Option([], "--alt", "-a", help="Alternatives considered (repeatable)"),
    consequences: list[str] = typer.Option([], "--cons", help="Consequences (repeatable)"),
    status: str = typer.Option("proposed", "--status", "-s", help="Status: proposed, accepted, rejected"),
    tags: list[str] = typer.Option([], "--tag", "-t", help="Tags (repeatable)"),
) -> None:
    """Record a new decision."""
    service = get_service()

    try:
        dec_status = DecisionStatus(status.lower())
    except ValueError:
        console.print(f"[red]Invalid status:[/red] {status}")
        console.print(f"Valid: {', '.join(s.value for s in DecisionStatus)}")
        raise typer.Exit(1) from None

    dec = service.record(
        title=title,
        context=context,
        decision=decision,
        rationale=rationale,
        alternatives=list(alternatives),
        consequences=list(consequences),
        status=dec_status,
        tags=list(tags),
    )

    console.print(f"[green]Recorded:[/green] {dec.title}")
    console.print(f"[dim]ID: {dec.id}[/dim]")


@app.command("list")
def list_decisions(
    status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
    project: str = typer.Option(None, "--project", "-p", help="Filter by project"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results"),
) -> None:
    """List recorded decisions."""
    service = get_service()

    dec_status = None
    if status:
        try:
            dec_status = DecisionStatus(status.lower())
        except ValueError:
            console.print(f"[red]Invalid status:[/red] {status}")
            raise typer.Exit(1) from None

    results = service.list_all(status=dec_status, project=project, limit=limit)

    if not results:
        console.print("[yellow]No decisions recorded yet.[/yellow]")
        console.print("\nRecord a decision:")
        console.print('  psn decision record "Use PostgreSQL for data storage"')
        raise typer.Exit(0)

    _print_decisions(results)

    # Show status summary
    counts = service.count_by_status()
    if counts:
        summary_parts = [f"{s}: {c}" for s, c in sorted(counts.items())]
        console.print(f"\n[dim]{' | '.join(summary_parts)}[/dim]")


@app.command("show")
def show_decision(
    decision_id: str = typer.Argument(..., help="Decision ID"),
    adr: bool = typer.Option(False, "--adr", help="Show as ADR markdown"),
) -> None:
    """Show decision details."""
    service = get_service()

    dec = service.get(decision_id)
    if not dec:
        console.print(f"[red]Decision not found:[/red] {decision_id}")
        raise typer.Exit(1)

    if adr:
        console.print(dec.to_adr())
        return

    # Show formatted details
    status_color = {
        DecisionStatus.PROPOSED: "yellow",
        DecisionStatus.ACCEPTED: "green",
        DecisionStatus.REJECTED: "red",
        DecisionStatus.SUPERSEDED: "blue",
        DecisionStatus.DEPRECATED: "dim",
    }
    color = status_color.get(dec.status, "white")

    console.print(Panel(f"[bold]{dec.title}[/bold]", subtitle=f"[{color}]{dec.status.value}[/{color}]"))

    console.print(f"\n[dim]ID:[/dim] {dec.id}")
    console.print(f"[dim]Created:[/dim] {dec.created_at.strftime('%Y-%m-%d %H:%M')}")

    if dec.tags:
        console.print(f"[dim]Tags:[/dim] {', '.join(dec.tags)}")

    if dec.context:
        console.print(f"\n[bold]Context:[/bold]\n{dec.context}")

    if dec.decision:
        console.print(f"\n[bold]Decision:[/bold]\n{dec.decision}")

    if dec.rationale:
        console.print(f"\n[bold]Rationale:[/bold]\n{dec.rationale}")

    if dec.alternatives:
        console.print("\n[bold]Alternatives Considered:[/bold]")
        for alt in dec.alternatives:
            console.print(f"  - {alt}")

    if dec.consequences:
        console.print("\n[bold]Consequences:[/bold]")
        for cons in dec.consequences:
            console.print(f"  - {cons}")


@app.command("search")
def search_decisions(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results"),
) -> None:
    """Search decisions by text."""
    service = get_service()

    results = service.search(query, limit=limit)

    if not results:
        console.print("[yellow]No matching decisions found.[/yellow]")
        raise typer.Exit(0)

    _print_decisions(results)


@app.command("accept")
def accept_decision(
    decision_id: str = typer.Argument(..., help="Decision ID"),
) -> None:
    """Accept a proposed decision."""
    service = get_service()

    dec = service.update_status(decision_id, DecisionStatus.ACCEPTED)
    if dec:
        console.print(f"[green]Accepted:[/green] {dec.title}")
    else:
        console.print(f"[red]Decision not found:[/red] {decision_id}")
        raise typer.Exit(1)


@app.command("reject")
def reject_decision(
    decision_id: str = typer.Argument(..., help="Decision ID"),
) -> None:
    """Reject a proposed decision."""
    service = get_service()

    dec = service.update_status(decision_id, DecisionStatus.REJECTED)
    if dec:
        console.print(f"[red]Rejected:[/red] {dec.title}")
    else:
        console.print(f"[red]Decision not found:[/red] {decision_id}")
        raise typer.Exit(1)


@app.command("supersede")
def supersede_decision(
    decision_id: str = typer.Argument(..., help="Decision ID"),
) -> None:
    """Mark a decision as superseded."""
    service = get_service()

    dec = service.update_status(decision_id, DecisionStatus.SUPERSEDED)
    if dec:
        console.print(f"[blue]Superseded:[/blue] {dec.title}")
    else:
        console.print(f"[red]Decision not found:[/red] {decision_id}")
        raise typer.Exit(1)


@app.command("remove")
def remove_decision(
    decision_id: str = typer.Argument(..., help="Decision ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a decision."""
    service = get_service()

    dec = service.get(decision_id)
    if not dec:
        console.print(f"[red]Decision not found:[/red] {decision_id}")
        raise typer.Exit(1)

    if not force:
        console.print(f"Remove: {dec.title}")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            raise typer.Exit(0)

    service.remove(decision_id)
    console.print(f"[green]Removed:[/green] {decision_id}")


@app.command("export")
def export_decisions(
    output_dir: Path = typer.Argument(Path("decisions"), help="Output directory for ADR files"),
) -> None:
    """Export all decisions as ADR markdown files."""
    service = get_service()

    count = service.export_all_adr(output_dir)

    if count == 0:
        console.print("[yellow]No decisions to export.[/yellow]")
    else:
        console.print(f"[green]Exported {count} decision(s) to {output_dir}/[/green]")


def _print_decisions(decisions: list) -> None:
    """Print a list of decisions as a table."""
    table = Table(title="Decisions")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Status", width=10)
    table.add_column("Title")
    table.add_column("Date", style="dim", width=10)

    status_style = {
        DecisionStatus.PROPOSED: "yellow",
        DecisionStatus.ACCEPTED: "green",
        DecisionStatus.REJECTED: "red",
        DecisionStatus.SUPERSEDED: "blue",
        DecisionStatus.DEPRECATED: "dim",
    }

    for dec in decisions:
        style = status_style.get(dec.status, "white")
        table.add_row(
            dec.id,
            f"[{style}]{dec.status.value}[/{style}]",
            dec.title[:50] + "..." if len(dec.title) > 50 else dec.title,
            dec.created_at.strftime("%Y-%m-%d"),
        )

    console.print(table)
