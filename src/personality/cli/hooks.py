"""Hooks CLI commands."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from personality.services.cart_registry import CartRegistry
from personality.services.persona_builder import PersonaBuilder

app = typer.Typer(invoke_without_command=True)
console = Console()

# =============================================================================
# Hook Logging Configuration
# =============================================================================

HOOKS_LOG_FILE = Path.home() / ".config" / "psn" / "hooks.jsonl"
LOGGING_CONFIG_FILE = Path.home() / ".config" / "psn" / "logging.toml"

# Defaults (used if no config file exists)
DEFAULT_MAX_LEN = 50
DEFAULT_PRESERVE_FIELDS = [
    "path", "file_path", "cwd", "transcript_path", "file", "directory"
]
DEFAULT_PRESERVE_SUFFIXES = ["_path", "_dir"]

# Cached config
_logging_config: dict | None = None


def _load_logging_config() -> dict:
    """Load logging configuration from TOML file."""
    global _logging_config

    if _logging_config is not None:
        return _logging_config

    config = {
        "max_length": DEFAULT_MAX_LEN,
        "preserve_fields": DEFAULT_PRESERVE_FIELDS.copy(),
        "preserve_suffixes": DEFAULT_PRESERVE_SUFFIXES.copy(),
    }

    if LOGGING_CONFIG_FILE.exists():
        try:
            import tomllib
            with LOGGING_CONFIG_FILE.open("rb") as f:
                file_config = tomllib.load(f)

            if "truncation" in file_config:
                t = file_config["truncation"]
                if "max_length" in t:
                    config["max_length"] = t["max_length"]
                if "preserve_fields" in t:
                    config["preserve_fields"] = t["preserve_fields"]
                if "preserve_suffixes" in t:
                    config["preserve_suffixes"] = t["preserve_suffixes"]
        except Exception:
            pass  # Use defaults on error

    _logging_config = config
    return config


def _truncate(value: str) -> str:
    """Truncate string to configured max_length, adding ... if truncated."""
    cfg = _load_logging_config()
    max_len = cfg["max_length"]
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _is_preserved_key(key: str) -> bool:
    """Check if key should be preserved (not truncated)."""
    cfg = _load_logging_config()
    key_lower = key.lower()

    # Check exact match
    if key_lower in cfg["preserve_fields"]:
        return True

    # Check suffix match
    for suffix in cfg["preserve_suffixes"]:
        if key_lower.endswith(suffix.lower()):
            return True

    return False


def _process_value(key: str, value: any) -> any:
    """Process a value for logging - truncate strings except preserved fields."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        if _is_preserved_key(key):
            return value  # Keep preserved fields intact
        return _truncate(value)
    if isinstance(value, dict):
        return {k: _process_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        # Truncate list to first 5 items, process each
        processed = [_process_value(key, item) for item in value[:5]]
        if len(value) > 5:
            processed.append(f"...+{len(value) - 5} more")
        return processed
    # Fallback: convert to string and truncate
    return _truncate(str(value))


def _read_stdin_json() -> dict | None:
    """Read JSON from stdin if available."""
    try:
        if not sys.stdin.isatty():
            return json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        pass
    return None


def _log_hook(event: str, stdin_data: dict | None = None) -> None:
    """Log hook invocation to JSONL file.

    Logs all fields from stdin, truncating strings to 50 chars (except paths).
    """
    HOOKS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "session": os.environ.get("CLAUDE_SESSION_ID", ""),
        "cwd": os.getcwd(),
    }

    if stdin_data:
        for key, value in stdin_data.items():
            if key in ("hook_event_name",):  # Skip redundant fields
                continue
            entry[key] = _process_value(key, value)

    try:
        with HOOKS_LOG_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Silent fail - don't break hooks on logging errors


# =============================================================================
# Session Tracking for Read Files
# =============================================================================

def _get_tracking_file() -> Path:
    """Get the tracking file path for the current session."""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    tracking_dir = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-read-tracking"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    return tracking_dir / f"{session_id}.txt"


def _get_read_files() -> set[str]:
    """Get the set of files that have been read this session."""
    tracking_file = _get_tracking_file()
    if tracking_file.exists():
        return set(tracking_file.read_text().strip().split("\n"))
    return set()


def _record_read_file(file_path: str) -> None:
    """Record that a file has been read."""
    tracking_file = _get_tracking_file()
    with tracking_file.open("a") as f:
        f.write(f"{file_path}\n")


# Prompts directory (relative to project root)
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"


# =============================================================================
# Main App
# =============================================================================

@app.callback(invoke_without_command=True)
def hooks_main(ctx: typer.Context) -> None:
    """Claude Code hooks management."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


# =============================================================================
# PreToolUse Hook
# =============================================================================

pre_tool_use_app = typer.Typer(help="Pre-tool-use hook", invoke_without_command=True)
app.add_typer(pre_tool_use_app, name="pre-tool-use")


@pre_tool_use_app.callback(invoke_without_command=True)
def pre_tool_use() -> None:
    """Hook called before tool execution."""
    stdin_data = _read_stdin_json()
    _log_hook("PreToolUse", stdin_data)


@pre_tool_use_app.command("require-read")
def pre_tool_use_require_read() -> None:
    """Block Write to existing files that haven't been read first.

    Reads tool input from stdin (JSON with file_path).
    Outputs blocking response if file exists but wasn't read.
    """
    # Read tool input from stdin
    try:
        tool_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        _log_hook("PreToolUse", {"tool": "Write", "cmd": "require-read"})
        return  # No input, allow

    file_path = tool_input.get("file_path")
    _log_hook("PreToolUse", {"tool": "Write", "cmd": "require-read", "file": file_path})

    if not file_path:
        return  # No file path, allow

    # Check if file exists
    target = Path(file_path)
    if not target.exists():
        return  # New file, allow

    # Check if file was read this session
    read_files = _get_read_files()
    if file_path in read_files or str(target.resolve()) in read_files:
        return  # File was read, allow

    # Block the write
    result = {
        "decision": "block",
        "reason": f"File '{file_path}' exists but hasn't been read. Read the file first before writing to it."
    }
    print(json.dumps(result))


# =============================================================================
# PostToolUse Hook
# =============================================================================

post_tool_use_app = typer.Typer(help="Post-tool-use hook")
app.add_typer(post_tool_use_app, name="post-tool-use")


@post_tool_use_app.callback(invoke_without_command=True)
def post_tool_use() -> None:
    """Hook called after tool execution."""
    stdin_data = _read_stdin_json()
    _log_hook("PostToolUse", stdin_data)


@post_tool_use_app.command("track-read")
def post_tool_use_track_read() -> None:
    """Track files that have been read for require-read validation.

    Reads tool input from stdin (JSON with file_path).
    Records the file path to the session tracking file.
    """
    # Read tool input from stdin
    try:
        tool_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        _log_hook("PostToolUse", {"tool": "Read", "cmd": "track-read"})
        return  # No input, nothing to track

    file_path = tool_input.get("file_path")
    _log_hook("PostToolUse", {"tool": "Read", "cmd": "track-read", "file": file_path})

    if not file_path:
        return  # No file path, nothing to track

    # Record that this file was read
    _record_read_file(file_path)
    # Also record resolved path for robustness
    try:
        resolved = str(Path(file_path).resolve())
        if resolved != file_path:
            _record_read_file(resolved)
    except Exception:
        pass  # Ignore resolution errors


# =============================================================================
# Stop Hook
# =============================================================================

stop_app = typer.Typer(help="Stop hook")
app.add_typer(stop_app, name="stop")


@stop_app.callback(invoke_without_command=True)
def stop() -> None:
    """Hook called when agent stops."""
    stdin_data = _read_stdin_json()
    _log_hook("Stop", stdin_data)


# =============================================================================
# SubagentStop Hook
# =============================================================================

subagent_stop_app = typer.Typer(help="Subagent-stop hook")
app.add_typer(subagent_stop_app, name="subagent-stop")


@subagent_stop_app.callback(invoke_without_command=True)
def subagent_stop() -> None:
    """Hook called when subagent stops."""
    stdin_data = _read_stdin_json()
    _log_hook("SubagentStop", stdin_data)


# =============================================================================
# SessionStart Hook
# =============================================================================

session_start_app = typer.Typer(help="Session-start hook")
app.add_typer(session_start_app, name="session-start")


@session_start_app.callback(invoke_without_command=True)
def session_start() -> None:
    """Hook called when session starts. Outputs intro prompt and persona instructions."""
    stdin_data = _read_stdin_json()
    _log_hook("SessionStart", stdin_data)

    output_parts = []

    # Try to load active persona
    try:
        registry = CartRegistry()
        cart = registry.get_active()

        if cart:
            # Build persona instructions
            persona_instructions = PersonaBuilder.build_instructions(cart)
            if persona_instructions:
                output_parts.append(persona_instructions)
                output_parts.append("\n---\n\n")

            # Add persona summary to intro
            summary = PersonaBuilder.build_summary(cart)
            output_parts.append(f"**Active Persona:** {summary}\n\n")
    except Exception:
        # Silently continue if cart loading fails
        pass

    # Load base intro
    intro_file = PROMPTS_DIR / "intro.md"
    if intro_file.exists():
        output_parts.append(intro_file.read_text())

    # Output combined prompt
    if output_parts:
        print("".join(output_parts))


# =============================================================================
# SessionEnd Hook
# =============================================================================

session_end_app = typer.Typer(help="Session-end hook")
app.add_typer(session_end_app, name="session-end")


@session_end_app.callback(invoke_without_command=True)
def session_end() -> None:
    """Hook called when session ends."""
    stdin_data = _read_stdin_json()
    _log_hook("SessionEnd", stdin_data)


# =============================================================================
# UserPromptSubmit Hook
# =============================================================================

user_prompt_submit_app = typer.Typer(help="User-prompt-submit hook")
app.add_typer(user_prompt_submit_app, name="user-prompt-submit")


@user_prompt_submit_app.callback(invoke_without_command=True)
def user_prompt_submit() -> None:
    """Hook called when user submits a prompt."""
    stdin_data = _read_stdin_json()
    _log_hook("UserPromptSubmit", stdin_data)


# =============================================================================
# PreCompact Hook
# =============================================================================

pre_compact_app = typer.Typer(help="Pre-compact hook")
app.add_typer(pre_compact_app, name="pre-compact")


@pre_compact_app.callback(invoke_without_command=True)
def pre_compact() -> None:
    """Hook called before context compaction."""
    stdin_data = _read_stdin_json()
    _log_hook("PreCompact", stdin_data)


# =============================================================================
# Notification Hook
# =============================================================================

notification_app = typer.Typer(help="Notification hook")
app.add_typer(notification_app, name="notification")


@notification_app.callback(invoke_without_command=True)
def notification() -> None:
    """Hook called for notifications."""
    stdin_data = _read_stdin_json()
    _log_hook("Notification", stdin_data)
