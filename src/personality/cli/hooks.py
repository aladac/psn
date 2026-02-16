"""Hooks CLI commands."""

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()


# Pre-tool-use hook
pre_tool_use_app = typer.Typer(help="Pre-tool-use hook")
app.add_typer(pre_tool_use_app, name="pre-tool-use")


@pre_tool_use_app.callback(invoke_without_command=True)
def pre_tool_use() -> None:
    """Hook called before tool execution."""
    pass


# Post-tool-use hook
post_tool_use_app = typer.Typer(help="Post-tool-use hook")
app.add_typer(post_tool_use_app, name="post-tool-use")


@post_tool_use_app.callback(invoke_without_command=True)
def post_tool_use() -> None:
    """Hook called after tool execution."""
    pass


# Stop hook
stop_app = typer.Typer(help="Stop hook")
app.add_typer(stop_app, name="stop")


@stop_app.callback(invoke_without_command=True)
def stop() -> None:
    """Hook called when agent stops."""
    pass


# Subagent-stop hook
subagent_stop_app = typer.Typer(help="Subagent-stop hook")
app.add_typer(subagent_stop_app, name="subagent-stop")


@subagent_stop_app.callback(invoke_without_command=True)
def subagent_stop() -> None:
    """Hook called when subagent stops."""
    pass


# Session-start hook
session_start_app = typer.Typer(help="Session-start hook")
app.add_typer(session_start_app, name="session-start")


@session_start_app.callback(invoke_without_command=True)
def session_start() -> None:
    """Hook called when session starts."""
    pass


# Session-end hook
session_end_app = typer.Typer(help="Session-end hook")
app.add_typer(session_end_app, name="session-end")


@session_end_app.callback(invoke_without_command=True)
def session_end() -> None:
    """Hook called when session ends."""
    pass


# User-prompt-submit hook
user_prompt_submit_app = typer.Typer(help="User-prompt-submit hook")
app.add_typer(user_prompt_submit_app, name="user-prompt-submit")


@user_prompt_submit_app.callback(invoke_without_command=True)
def user_prompt_submit() -> None:
    """Hook called when user submits a prompt."""
    pass


# Pre-compact hook
pre_compact_app = typer.Typer(help="Pre-compact hook")
app.add_typer(pre_compact_app, name="pre-compact")


@pre_compact_app.callback(invoke_without_command=True)
def pre_compact() -> None:
    """Hook called before context compaction."""
    pass


# Notification hook
notification_app = typer.Typer(help="Notification hook")
app.add_typer(notification_app, name="notification")


@notification_app.callback(invoke_without_command=True)
def notification() -> None:
    """Hook called for notifications."""
    pass
