"""Indexing CLI commands with AST analysis."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from personality.analyzer import analyze_file, generate_symbol_id

app = typer.Typer(invoke_without_command=True)
console = Console()


def get_indexer():
    """Lazy import indexer module."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "servers"))
    import indexer

    return indexer


def ensure_symbols_table(indexer) -> None:
    """Ensure the symbols table exists."""
    sql = """
    CREATE TABLE IF NOT EXISTS symbols (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        signature TEXT,
        start_line INTEGER,
        end_line INTEGER,
        docstring TEXT,
        parent TEXT,
        project TEXT,
        embedding vector(768),
        indexed_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS symbols_path_idx ON symbols (path);
    CREATE INDEX IF NOT EXISTS symbols_name_idx ON symbols (name);
    CREATE INDEX IF NOT EXISTS symbols_kind_idx ON symbols (kind);
    CREATE INDEX IF NOT EXISTS symbols_project_idx ON symbols (project);
    CREATE INDEX IF NOT EXISTS symbols_embedding_idx ON symbols USING ivfflat (embedding vector_cosine_ops);

    CREATE TABLE IF NOT EXISTS imports (
        id SERIAL PRIMARY KEY,
        source_path TEXT NOT NULL,
        imported TEXT NOT NULL,
        project TEXT,
        indexed_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS imports_source_idx ON imports (source_path);
    CREATE INDEX IF NOT EXISTS imports_imported_idx ON imports (imported);

    CREATE TABLE IF NOT EXISTS calls (
        id SERIAL PRIMARY KEY,
        source_path TEXT NOT NULL,
        callee TEXT NOT NULL,
        project TEXT,
        indexed_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS calls_source_idx ON calls (source_path);
    CREATE INDEX IF NOT EXISTS calls_callee_idx ON calls (callee);
    """
    indexer.run_psql(sql)


@app.callback(invoke_without_command=True)
def index_main(ctx: typer.Context) -> None:
    """Code indexing commands."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("file")
def index_file(
    file_path: str = typer.Argument(None, help="File to index"),
    project: str = typer.Option(None, "--project", "-p", help="Project name"),
    analyze: bool = typer.Option(True, "--analyze/--no-analyze", help="Run AST analysis"),
) -> None:
    """Index a single file with optional AST analysis."""
    if not file_path:
        console.print("[red]File path required[/red]")
        raise typer.Exit(1) from None

    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1) from None

    try:
        indexer = get_indexer()
        ensure_symbols_table(indexer)

        ext = path.suffix.lower()
        content = path.read_text()
        project_name = project or "default"

        # Index raw content with embedding
        if ext in indexer.CODE_EXTENSIONS:
            file_id = f"{project_name}:{file_path}"
            embedding = indexer.get_embedding(content)

            if embedding:
                vec_str = "[" + ",".join(map(str, embedding)) + "]"
                sql = f"""
                    INSERT INTO code_index (id, path, content, embedding, language, project)
                    VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{ext[1:]}', '{project_name}')
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        indexed_at = NOW()
                """
                indexer.run_psql(sql)
                console.print(f"[green]✓[/green] Indexed content: {path.name}")

            # Run AST analysis
            if analyze:
                result = analyze_file(path)
                if result and not result.errors:
                    # Clear old symbols/imports/calls for this file
                    indexer.run_psql(f"DELETE FROM symbols WHERE path = '{file_path}'")
                    indexer.run_psql(f"DELETE FROM imports WHERE source_path = '{file_path}'")
                    indexer.run_psql(f"DELETE FROM calls WHERE source_path = '{file_path}'")

                    # Insert symbols
                    for sym in result.symbols:
                        sym_id = generate_symbol_id(file_path, sym.name, sym.kind)
                        # Generate embedding for signature + docstring
                        sym_text = f"{sym.signature}\n{sym.docstring or ''}"
                        sym_embedding = indexer.get_embedding(sym_text)

                        vec_str = ""
                        if sym_embedding:
                            vec_str = ", embedding = '[" + ",".join(map(str, sym_embedding)) + "]'"

                        docstring_escaped = (sym.docstring or "").replace("'", "''")[:2000]
                        sql = f"""
                            INSERT INTO symbols (id, path, name, kind, signature, start_line, end_line, docstring, parent, project)
                            VALUES (
                                '{sym_id}', '{file_path}', '{sym.name}', '{sym.kind}',
                                '{sym.signature.replace("'", "''")}', {sym.start_line}, {sym.end_line},
                                '{docstring_escaped}', '{sym.parent or ""}', '{project_name}'
                            )
                            ON CONFLICT (id) DO UPDATE SET
                                signature = EXCLUDED.signature,
                                start_line = EXCLUDED.start_line,
                                end_line = EXCLUDED.end_line,
                                docstring = EXCLUDED.docstring,
                                indexed_at = NOW()
                                {vec_str}
                        """
                        indexer.run_psql(sql)

                    # Insert imports
                    for imp in result.imports:
                        sql = f"""
                            INSERT INTO imports (source_path, imported, project)
                            VALUES ('{file_path}', '{imp}', '{project_name}')
                        """
                        indexer.run_psql(sql)

                    # Insert calls
                    for call in result.calls:
                        sql = f"""
                            INSERT INTO calls (source_path, callee, project)
                            VALUES ('{file_path}', '{call}', '{project_name}')
                        """
                        indexer.run_psql(sql)

                    console.print(
                        f"[green]✓[/green] Analyzed: {len(result.symbols)} symbols, {len(result.imports)} imports, {len(result.calls)} calls"
                    )
                elif result and result.errors:
                    console.print(f"[yellow]⚠[/yellow] Analysis errors: {result.errors[0]}")

        elif ext in indexer.DOC_EXTENSIONS:
            file_id = f"{project_name}:{file_path}"
            embedding = indexer.get_embedding(content)

            if embedding:
                vec_str = "[" + ",".join(map(str, embedding)) + "]"
                sql = f"""
                    INSERT INTO doc_index (id, path, content, embedding, project)
                    VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{project_name}')
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        indexed_at = NOW()
                """
                indexer.run_psql(sql)
                console.print(f"[green]✓[/green] Indexed: {path.name}")
        else:
            console.print(f"[dim]Skipped {path.name} (unsupported extension)[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("hook")
def index_hook() -> None:
    """Index file from PostToolUse hook (reads JSON from stdin)."""
    try:
        data = json.load(sys.stdin)
        file_path = data.get("tool_input", {}).get("file_path")
        cwd = data.get("cwd", "")

        if not file_path:
            return

        project = Path(cwd).name if cwd else "default"
        ext = Path(file_path).suffix.lower()
        indexer = get_indexer()

        if ext not in indexer.CODE_EXTENSIONS and ext not in indexer.DOC_EXTENSIONS:
            return

        path = Path(file_path)
        if not path.exists():
            return

        ensure_symbols_table(indexer)
        content = path.read_text()
        embedding = indexer.get_embedding(content)

        if not embedding:
            return

        file_id = f"{project}:{file_path}"
        vec_str = "[" + ",".join(map(str, embedding)) + "]"

        # Index content
        if ext in indexer.CODE_EXTENSIONS:
            sql = f"""
                INSERT INTO code_index (id, path, content, embedding, language, project)
                VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{ext[1:]}', '{project}')
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    indexed_at = NOW()
            """
            indexer.run_psql(sql)

            # Run analysis
            result = analyze_file(path)
            if result and not result.errors:
                indexer.run_psql(f"DELETE FROM symbols WHERE path = '{file_path}'")
                indexer.run_psql(f"DELETE FROM imports WHERE source_path = '{file_path}'")
                indexer.run_psql(f"DELETE FROM calls WHERE source_path = '{file_path}'")

                for sym in result.symbols:
                    sym_id = generate_symbol_id(file_path, sym.name, sym.kind)
                    docstring_escaped = (sym.docstring or "").replace("'", "''")[:2000]
                    sql = f"""
                        INSERT INTO symbols (id, path, name, kind, signature, start_line, end_line, docstring, parent, project)
                        VALUES (
                            '{sym_id}', '{file_path}', '{sym.name}', '{sym.kind}',
                            '{sym.signature.replace("'", "''")}', {sym.start_line}, {sym.end_line},
                            '{docstring_escaped}', '{sym.parent or ""}', '{project}'
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            signature = EXCLUDED.signature,
                            indexed_at = NOW()
                    """
                    indexer.run_psql(sql)

                for imp in result.imports:
                    indexer.run_psql(
                        f"INSERT INTO imports (source_path, imported, project) VALUES ('{file_path}', '{imp}', '{project}')"
                    )

                for call in result.calls:
                    indexer.run_psql(
                        f"INSERT INTO calls (source_path, callee, project) VALUES ('{file_path}', '{call}', '{project}')"
                    )
        else:
            sql = f"""
                INSERT INTO doc_index (id, path, content, embedding, project)
                VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{project}')
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    indexed_at = NOW()
            """
            indexer.run_psql(sql)

        print(json.dumps({"indexed": file_path, "analyzed": ext in indexer.CODE_EXTENSIONS}))

    except Exception:
        pass


@app.command("symbols")
def list_symbols(
    path: str = typer.Option(None, "--path", "-f", help="Filter by file path"),
    kind: str = typer.Option(None, "--kind", "-k", help="Filter by kind (function/class/method)"),
    project: str = typer.Option(None, "--project", "-p", help="Filter by project"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
) -> None:
    """List indexed symbols."""
    try:
        indexer = get_indexer()

        sql = "SELECT name, kind, signature, path, start_line FROM symbols WHERE 1=1"
        if path:
            sql += f" AND path LIKE '%{path}%'"
        if kind:
            sql += f" AND kind = '{kind}'"
        if project:
            sql += f" AND project = '{project}'"
        sql += f" ORDER BY path, start_line LIMIT {limit}"

        result = indexer.run_psql(sql)
        if result.get("success") and result.get("stdout"):
            for line in result["stdout"].strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        console.print(
                            f"[cyan]{parts[1]}[/cyan] {parts[0]}: {parts[2]} ({parts[3]}:{parts[4] if len(parts) > 4 else '?'})"
                        )
        else:
            console.print("[dim]No symbols found[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command("deps")
def show_deps(
    path: str = typer.Argument(..., help="File path to show dependencies for"),
) -> None:
    """Show imports and dependencies for a file."""
    try:
        indexer = get_indexer()

        # Get imports
        sql = f"SELECT imported FROM imports WHERE source_path = '{path}'"
        result = indexer.run_psql(sql)

        console.print(f"[bold]Imports in {path}:[/bold]")
        if result.get("success") and result.get("stdout"):
            for line in result["stdout"].strip().split("\n"):
                if line:
                    console.print(f"  {line}")
        else:
            console.print("  [dim]None[/dim]")

        # Get calls
        sql = f"SELECT DISTINCT callee FROM calls WHERE source_path = '{path}'"
        result = indexer.run_psql(sql)

        console.print("\n[bold]Function calls:[/bold]")
        if result.get("success") and result.get("stdout"):
            for line in result["stdout"].strip().split("\n"):
                if line:
                    console.print(f"  {line}")
        else:
            console.print("  [dim]None[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command("callers")
def show_callers(
    name: str = typer.Argument(..., help="Function/method name"),
    project: str = typer.Option(None, "--project", "-p", help="Filter by project"),
) -> None:
    """Show files that call a function."""
    try:
        indexer = get_indexer()

        sql = f"SELECT DISTINCT source_path FROM calls WHERE callee = '{name}'"
        if project:
            sql += f" AND project = '{project}'"

        result = indexer.run_psql(sql)

        console.print(f"[bold]Files calling '{name}':[/bold]")
        if result.get("success") and result.get("stdout"):
            for line in result["stdout"].strip().split("\n"):
                if line:
                    console.print(f"  {line}")
        else:
            console.print("  [dim]None found[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command("diff")
def show_diff(
    path: str = typer.Argument(".", help="Directory to check"),
    project: str = typer.Option(None, "--project", "-p", help="Project name"),
    index_type: str = typer.Option("all", "--type", "-t", help="Type: code, docs, all"),
) -> None:
    """Show files changed since last index."""
    try:
        indexer = get_indexer()
        project_name = project or Path(path).resolve().name
        base_path = Path(path).resolve()

        # Get indexed files with timestamps
        indexed_code = {}
        indexed_docs = {}

        if index_type in ("code", "all"):
            sql = f"SELECT path, indexed_at FROM code_index WHERE project = '{project_name}'"
            result = indexer.run_psql(sql)
            if result.get("success") and result.get("stdout"):
                for line in result["stdout"].strip().split("\n"):
                    if line and "|" in line:
                        parts = line.split("|")
                        indexed_code[parts[0]] = parts[1] if len(parts) > 1 else None

        if index_type in ("docs", "all"):
            sql = f"SELECT path, indexed_at FROM doc_index WHERE project = '{project_name}'"
            result = indexer.run_psql(sql)
            if result.get("success") and result.get("stdout"):
                for line in result["stdout"].strip().split("\n"):
                    if line and "|" in line:
                        parts = line.split("|")
                        indexed_docs[parts[0]] = parts[1] if len(parts) > 1 else None

        # Scan filesystem
        new_files = []
        modified_files = []
        deleted_files = []

        extensions = set()
        if index_type in ("code", "all"):
            extensions.update(indexer.CODE_EXTENSIONS)
        if index_type in ("docs", "all"):
            extensions.update(indexer.DOC_EXTENSIONS)

        current_files = set()
        for file_path in base_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in extensions:
                continue
            # Skip hidden/vendor directories
            if any(
                p.startswith(".") or p in ("node_modules", "vendor", "__pycache__", ".git") for p in file_path.parts
            ):
                continue

            str_path = str(file_path)
            current_files.add(str_path)
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)

            # Check if in index
            indexed = indexed_code if file_path.suffix.lower() in indexer.CODE_EXTENSIONS else indexed_docs

            if str_path not in indexed:
                new_files.append(str_path)
            else:
                # Compare timestamps
                indexed_at_str = indexed[str_path]
                if indexed_at_str:
                    try:
                        # Parse PostgreSQL timestamp
                        indexed_at = datetime.fromisoformat(indexed_at_str.replace(" ", "T").split(".")[0])
                        indexed_at = indexed_at.replace(tzinfo=UTC)
                        if mtime > indexed_at:
                            modified_files.append(str_path)
                    except (ValueError, TypeError):
                        modified_files.append(str_path)

        # Find deleted files
        all_indexed = set(indexed_code.keys()) | set(indexed_docs.keys())
        for indexed_path in all_indexed:
            if indexed_path.startswith(str(base_path)) and indexed_path not in current_files:
                deleted_files.append(indexed_path)

        # Display results
        table = Table(title=f"Index Diff: {project_name}")
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Files")

        if new_files:
            table.add_row(
                "[green]New[/green]",
                str(len(new_files)),
                "\n".join(new_files[:5]) + ("..." if len(new_files) > 5 else ""),
            )
        if modified_files:
            table.add_row(
                "[yellow]Modified[/yellow]",
                str(len(modified_files)),
                "\n".join(modified_files[:5]) + ("..." if len(modified_files) > 5 else ""),
            )
        if deleted_files:
            table.add_row(
                "[red]Deleted[/red]",
                str(len(deleted_files)),
                "\n".join(deleted_files[:5]) + ("..." if len(deleted_files) > 5 else ""),
            )

        if not new_files and not modified_files and not deleted_files:
            console.print("[green]✓[/green] Index is up to date")
        else:
            console.print(table)
            total = len(new_files) + len(modified_files) + len(deleted_files)
            console.print(f"\n[bold]{total}[/bold] files need re-indexing")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("sync")
def sync_index(
    path: str = typer.Argument(".", help="Directory to sync"),
    project: str = typer.Option(None, "--project", "-p", help="Project name"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be indexed"),
) -> None:
    """Re-index all changed files since last index."""
    try:
        indexer = get_indexer()
        ensure_symbols_table(indexer)
        project_name = project or Path(path).resolve().name
        base_path = Path(path).resolve()

        # Get indexed files with timestamps
        indexed = {}
        for table in ("code_index", "doc_index"):
            sql = f"SELECT path, indexed_at FROM {table} WHERE project = '{project_name}'"
            result = indexer.run_psql(sql)
            if result.get("success") and result.get("stdout"):
                for line in result["stdout"].strip().split("\n"):
                    if line and "|" in line:
                        parts = line.split("|")
                        indexed[parts[0]] = parts[1] if len(parts) > 1 else None

        # Find files to index
        to_index = []
        extensions = indexer.CODE_EXTENSIONS | indexer.DOC_EXTENSIONS

        for file_path in base_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in extensions:
                continue
            if any(
                p.startswith(".") or p in ("node_modules", "vendor", "__pycache__", ".git") for p in file_path.parts
            ):
                continue

            str_path = str(file_path)
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)

            if str_path not in indexed:
                to_index.append(file_path)
            else:
                indexed_at_str = indexed[str_path]
                if indexed_at_str:
                    try:
                        indexed_at = datetime.fromisoformat(indexed_at_str.replace(" ", "T").split(".")[0])
                        indexed_at = indexed_at.replace(tzinfo=UTC)
                        if mtime > indexed_at:
                            to_index.append(file_path)
                    except (ValueError, TypeError):
                        to_index.append(file_path)

        if not to_index:
            console.print("[green]✓[/green] Index is up to date")
            return

        if dry_run:
            console.print(f"[bold]Would index {len(to_index)} files:[/bold]")
            for f in to_index[:20]:
                console.print(f"  {f}")
            if len(to_index) > 20:
                console.print(f"  ... and {len(to_index) - 20} more")
            return

        # Index files
        console.print(f"[bold]Indexing {len(to_index)} files...[/bold]")
        indexed_count = 0
        error_count = 0

        for file_path in to_index:
            try:
                ext = file_path.suffix.lower()
                content = file_path.read_text(errors="ignore")
                str_path = str(file_path)
                file_id = f"{project_name}:{str_path}"

                embedding = indexer.get_embedding(content)
                if not embedding:
                    error_count += 1
                    continue

                vec_str = "[" + ",".join(map(str, embedding)) + "]"

                if ext in indexer.CODE_EXTENSIONS:
                    sql = f"""
                        INSERT INTO code_index (id, path, content, embedding, language, project)
                        VALUES ('{file_id}', '{str_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{ext[1:]}', '{project_name}')
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content, embedding = EXCLUDED.embedding, indexed_at = NOW()
                    """
                    indexer.run_psql(sql)

                    # Analyze
                    result = analyze_file(file_path)
                    if result and not result.errors:
                        indexer.run_psql(f"DELETE FROM symbols WHERE path = '{str_path}'")
                        indexer.run_psql(f"DELETE FROM imports WHERE source_path = '{str_path}'")
                        indexer.run_psql(f"DELETE FROM calls WHERE source_path = '{str_path}'")

                        for sym in result.symbols:
                            sym_id = generate_symbol_id(str_path, sym.name, sym.kind)
                            docstring_escaped = (sym.docstring or "").replace("'", "''")[:2000]
                            sql = f"""
                                INSERT INTO symbols (id, path, name, kind, signature, start_line, end_line, docstring, parent, project)
                                VALUES ('{sym_id}', '{str_path}', '{sym.name}', '{sym.kind}',
                                        '{sym.signature.replace("'", "''")}', {sym.start_line}, {sym.end_line},
                                        '{docstring_escaped}', '{sym.parent or ""}', '{project_name}')
                                ON CONFLICT (id) DO UPDATE SET signature = EXCLUDED.signature, indexed_at = NOW()
                            """
                            indexer.run_psql(sql)

                        for imp in result.imports:
                            indexer.run_psql(
                                f"INSERT INTO imports (source_path, imported, project) VALUES ('{str_path}', '{imp}', '{project_name}')"
                            )

                        for call in result.calls:
                            indexer.run_psql(
                                f"INSERT INTO calls (source_path, callee, project) VALUES ('{str_path}', '{call}', '{project_name}')"
                            )
                else:
                    sql = f"""
                        INSERT INTO doc_index (id, path, content, embedding, project)
                        VALUES ('{file_id}', '{str_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{project_name}')
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content, embedding = EXCLUDED.embedding, indexed_at = NOW()
                    """
                    indexer.run_psql(sql)

                indexed_count += 1
                console.print(f"[green]✓[/green] {file_path.name}")

            except Exception as e:
                console.print(f"[red]✗[/red] {file_path.name}: {e}")
                error_count += 1

        console.print(f"\n[bold]Done:[/bold] {indexed_count} indexed, {error_count} errors")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
