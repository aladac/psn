---
description: 'Use when building Python command-line applications, creating CLI tools with Typer, or implementing terminal interfaces in Python.'
---

# Python CLI Development

Best practices for Python command-line applications using Typer.

## Framework: Typer

Typer is the modern CLI framework built on Click with type hints:

```python
# src/myapp/cli.py
import typer
from typing import Optional
from pathlib import Path
from myapp import __version__

app = typer.Typer(help="MyApp - Does useful things")

def version_callback(value: bool) -> None:
    if value:
        print(f"myapp {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    ),
) -> None:
    """MyApp CLI."""
    pass

@app.command()
def process(
    file: Path = typer.Argument(..., help="File to process"),
    output: Optional[Path] = typer.Option(None, "-o", "--output"),
    verbose: bool = typer.Option(False, "-V", "--verbose"),
) -> None:
    """Process a file."""
    if verbose:
        typer.echo(f"Processing {file}...")
    result = do_process(file)
    if output:
        output.write_text(result)
    else:
        typer.echo(result)

if __name__ == "__main__":
    app()
```

## Required Flags

| Flag | Purpose |
|------|---------|
| `--version`, `-v` | Show package version |
| `--help`, `-h` | Show usage (Typer provides automatically) |

## Subcommands

```python
app = typer.Typer()
config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    config = load_config()
    print_config(config)

@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    config = load_config()
    config[key] = value
    save_config(config)
```

## Output Patterns

### Colorized Output

```python
from rich.console import Console

console = Console()

def success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")

def error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}", style="red")

def warn(message: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {message}")
```

### Tables

```python
from rich.table import Table

def list_items(items: list[Item]) -> None:
    table = Table(title="Items")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Status", style="green")
    for item in items:
        table.add_row(item.id, item.name, item.status)
    console.print(table)
```

### Progress Bars

```python
from rich.progress import track

def process_files(files: list[Path]) -> None:
    for file in track(files, description="Processing..."):
        process(file)
```

## Configuration

### TOML Config Files

```python
from pathlib import Path
import tomllib
import tomli_w

CONFIG_PATH = Path.home() / ".config" / "myapp" / "config.toml"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return tomllib.loads(CONFIG_PATH.read_text())

def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(tomli_w.dumps(config))
```

### Environment Variables (Pydantic)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    debug: bool = False
    timeout: int = 30

    class Config:
        env_prefix = "MYAPP_"
        env_file = ".env"

settings = Settings()
```

## Error Handling

```python
@app.command()
def process(file: Path) -> None:
    try:
        result = processor.run(file)
        success(f"Processed {file}")
    except FileNotFoundError:
        error(f"File not found: {file}")
        raise typer.Exit(1)
    except ProcessingError as e:
        error(str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        warn("Aborted")
        raise typer.Exit(130)
```

## Interactive Prompts

```python
from rich.prompt import Prompt, Confirm

api_key = Prompt.ask("API Key", password=True)
env = Prompt.ask("Environment", choices=["dev", "staging", "prod"], default="dev")

if Confirm.ask("Save configuration?"):
    save_config(...)
```

## pyproject.toml Setup

```toml
[project]
name = "myapp"
version = "0.1.0"

[project.scripts]
myapp = "myapp.cli:app"

[project.dependencies]
typer = ">=0.9"
rich = ">=13"
tomli-w = ">=1.0"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=4.1"]
```

## Project Structure

```
myapp/
├── src/
│   └── myapp/
│       ├── __init__.py      # __version__
│       ├── cli.py           # Typer app
│       ├── config.py        # Configuration handling
│       └── commands/        # Complex command implementations
├── tests/
│   ├── test_cli.py
│   └── test_process.py
└── pyproject.toml
```

## Testing CLIs

```python
from typer.testing import CliRunner
from myapp.cli import app

runner = CliRunner()

def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "myapp" in result.stdout

def test_process_file(tmp_path):
    test_file = tmp_path / "input.txt"
    test_file.write_text("test content")
    result = runner.invoke(app, ["process", str(test_file)])
    assert result.exit_code == 0
```

## Summary

| Component | Library |
|-----------|---------|
| CLI framework | `typer` |
| Rich output | `rich` |
| Config | `tomllib` + `tomli-w` |
| Settings | `pydantic-settings` |
| Testing | `typer.testing.CliRunner` |
