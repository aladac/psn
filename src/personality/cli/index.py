"""Indexing CLI commands."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(invoke_without_command=True)
console = Console()

# Import indexer functions (lazy to avoid import errors if deps missing)
def get_indexer():
    """Lazy import indexer module."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "servers"))
    import indexer
    return indexer


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
) -> None:
    """Index a single file."""
    if not file_path:
        console.print("[red]File path required[/red]")
        raise typer.Exit(1)
    
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)
    
    try:
        indexer = get_indexer()
        
        # Determine file type
        ext = path.suffix.lower()
        content = path.read_text()
        
        if ext in indexer.CODE_EXTENSIONS:
            # Index as code
            file_id = f"{project or 'default'}:{file_path}"
            embedding = indexer.get_embedding(content)
            
            if embedding:
                vec_str = "[" + ",".join(map(str, embedding)) + "]"
                sql = f"""
                    INSERT INTO code_index (id, path, content, embedding, language, project)
                    VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{ext[1:]}', '{project or "default"}')
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        indexed_at = NOW()
                """
                result = indexer.run_psql(sql)
                if result.get("success"):
                    console.print(f"[green]✓[/green] Indexed {path.name}")
                else:
                    console.print(f"[red]✗[/red] Failed: {result.get('stderr', 'Unknown error')}")
            else:
                console.print(f"[yellow]⚠[/yellow] No embedding generated for {path.name}")
                
        elif ext in indexer.DOC_EXTENSIONS:
            # Index as doc
            file_id = f"{project or 'default'}:{file_path}"
            embedding = indexer.get_embedding(content)
            
            if embedding:
                vec_str = "[" + ",".join(map(str, embedding)) + "]"
                sql = f"""
                    INSERT INTO doc_index (id, path, content, embedding, project)
                    VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{project or "default"}')
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        indexed_at = NOW()
                """
                result = indexer.run_psql(sql)
                if result.get("success"):
                    console.print(f"[green]✓[/green] Indexed {path.name}")
                else:
                    console.print(f"[red]✗[/red] Failed: {result.get('stderr')}")
            else:
                console.print(f"[yellow]⚠[/yellow] No embedding generated")
        else:
            console.print(f"[dim]Skipped {path.name} (unsupported extension)[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("hook")
def index_hook() -> None:
    """Index file from PostToolUse hook (reads JSON from stdin)."""
    try:
        data = json.load(sys.stdin)
        file_path = data.get("tool_input", {}).get("file_path")
        cwd = data.get("cwd", "")
        
        if not file_path:
            return  # No file path in input
        
        # Determine project from cwd
        project = Path(cwd).name if cwd else None
        
        # Check if file type is indexable
        ext = Path(file_path).suffix.lower()
        indexer = get_indexer()
        
        if ext not in indexer.CODE_EXTENSIONS and ext not in indexer.DOC_EXTENSIONS:
            return  # Skip non-indexable files
        
        # Index the file (suppress output for hook)
        path = Path(file_path)
        if not path.exists():
            return
            
        content = path.read_text()
        embedding = indexer.get_embedding(content)
        
        if not embedding:
            return
            
        file_id = f"{project or 'default'}:{file_path}"
        vec_str = "[" + ",".join(map(str, embedding)) + "]"
        
        if ext in indexer.CODE_EXTENSIONS:
            table = "code_index"
            extra_cols = ", language"
            extra_vals = f", '{ext[1:]}'"
        else:
            table = "doc_index"
            extra_cols = ""
            extra_vals = ""
        
        sql = f"""
            INSERT INTO {table} (id, path, content, embedding, project{extra_cols})
            VALUES ('{file_id}', '{file_path}', '{content[:10000].replace("'", "''")}', '{vec_str}', '{project or "default"}'{extra_vals})
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                indexed_at = NOW()
        """
        indexer.run_psql(sql)
        
        # Output for Claude to see (optional)
        print(json.dumps({"indexed": file_path}))
        
    except Exception:
        pass  # Silently fail for hooks
