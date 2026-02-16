"""MCP server implementation for personality plugin."""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent

# Create the server instance
server = Server("personality")


def create_server() -> Server:
    """Create and return the MCP server instance."""
    return server


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all available resources."""
    return [
        Resource(
            uri="persona://current/memories",
            name="Current Persona Memories",
            description="List of memories from the active persona cartridge",
            mimeType="application/json",
        ),
        Resource(
            uri="persona://current/identity",
            name="Current Persona Identity",
            description="Identity information from the active persona",
            mimeType="application/json",
        ),
        Resource(
            uri="persona://current/cart",
            name="Current Cart",
            description="Full details of the active persona cartridge",
            mimeType="application/json",
        ),
        Resource(
            uri="persona://current/project",
            name="Current Project",
            description="Details about the current project",
            mimeType="application/json",
        ),
        Resource(
            uri="persona://user",
            name="User Info",
            description="Current user details (uid, gid, groups, name)",
            mimeType="application/json",
        ),
        Resource(
            uri="persona://host",
            name="Host Info",
            description="Host system information (uname, uptime)",
            mimeType="application/json",
        ),
        Resource(
            uri="knowledge://triples",
            name="Knowledge Triples",
            description="Knowledge graph triples",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> list[TextContent]:
    """Read a resource by URI."""
    import json

    # Dispatch to appropriate handler based on URI
    if uri == "persona://current/memories":
        data = await _get_current_memories()
    elif uri == "persona://current/identity":
        data = await _get_current_identity()
    elif uri == "persona://current/cart":
        data = await _get_current_cart()
    elif uri == "persona://current/project":
        data = await _get_current_project()
    elif uri == "persona://user":
        data = await _get_user_info()
    elif uri == "persona://host":
        data = await _get_host_info()
    elif uri == "knowledge://triples":
        data = await _get_knowledge_triples()
    else:
        data = {"error": f"Unknown resource: {uri}"}

    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


async def _get_current_memories() -> dict:
    """Get memories from active persona."""
    from personality.services.cart_registry import CartRegistry

    try:
        registry = CartRegistry()
        cart = registry.get_active()
        if not cart:
            return {"memories": [], "count": 0, "message": "No active cart"}

        memories = [{"subject": m.subject, "content": m.content, "source": m.source} for m in cart.persona.memories]
        return {"memories": memories, "count": len(memories), "cart": cart.tag}
    except Exception as e:
        return {"error": str(e)}


async def _get_current_identity() -> dict:
    """Get identity from active persona."""
    from personality.services.cart_registry import CartRegistry

    try:
        registry = CartRegistry()
        cart = registry.get_active()
        if not cart:
            return {"identity": None, "message": "No active cart"}

        identity = cart.preferences.identity
        return {
            "name": identity.name,
            "full_name": identity.full_name,
            "type": identity.type,
            "tagline": identity.tagline,
            "voice": cart.voice,
            "tts_enabled": cart.preferences.tts.enabled,
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_current_cart() -> dict:
    """Get full cart details."""
    from personality.services.cart_registry import CartRegistry

    try:
        registry = CartRegistry()
        cart = registry.get_active()
        if not cart:
            available = registry.list_available()
            return {
                "active": None,
                "available": [c.get("tag") for c in available],
                "message": "No active cart",
            }

        return {
            "tag": cart.tag,
            "version": cart.manifest.version,
            "memory_count": cart.memory_count,
            "voice": cart.voice,
            "path": str(cart.path) if cart.path else None,
            "identity": {
                "name": cart.preferences.identity.name,
                "type": cart.preferences.identity.type,
            },
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_current_project() -> dict:
    """Get current project details."""
    import os
    import subprocess
    from pathlib import Path

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    project_path = Path(project_dir)

    result = {
        "name": project_path.name,
        "path": str(project_path),
        "language": None,
        "framework": None,
        "git": None,
    }

    # Detect language
    if (project_path / "pyproject.toml").exists():
        result["language"] = "python"
    elif (project_path / "package.json").exists():
        result["language"] = "javascript"
    elif (project_path / "Cargo.toml").exists():
        result["language"] = "rust"
    elif (project_path / "Gemfile").exists():
        result["language"] = "ruby"
    elif (project_path / "go.mod").exists():
        result["language"] = "go"

    # Git info
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5,
        )
        if branch.returncode == 0:
            result["git"] = {"branch": branch.stdout.strip()}
    except Exception:
        pass

    return result


async def _get_user_info() -> dict:
    """Get current user information."""
    import grp
    import os
    import pwd

    uid = os.getuid()
    gid = os.getgid()

    try:
        pw = pwd.getpwuid(uid)
        username = pw.pw_name
        real_name = pw.pw_gecos.split(",")[0] if pw.pw_gecos else username
        home = pw.pw_dir
        shell = pw.pw_shell
    except KeyError:
        username = os.environ.get("USER", "unknown")
        real_name = username
        home = os.environ.get("HOME", "")
        shell = os.environ.get("SHELL", "")

    # Get groups
    groups = []
    try:
        group_ids = os.getgroups()
        for gid_item in group_ids:
            try:
                groups.append(grp.getgrgid(gid_item).gr_name)
            except KeyError:
                groups.append(str(gid_item))
    except Exception:
        pass

    return {
        "uid": uid,
        "gid": gid,
        "username": username,
        "real_name": real_name,
        "home": home,
        "shell": shell,
        "groups": groups,
    }


async def _get_host_info() -> dict:
    """Get host system information."""
    import os
    import platform
    import subprocess
    from datetime import UTC, datetime

    uname = platform.uname()

    result = {
        "system": uname.system,
        "node": uname.node,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor,
        "datetime": datetime.now(UTC).isoformat(),
        "uptime": None,
    }

    # Get uptime
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])
                result["uptime"] = uptime_seconds
        else:
            # macOS
            uptime_out = subprocess.run(
                ["uptime"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if uptime_out.returncode == 0:
                result["uptime_raw"] = uptime_out.stdout.strip()
    except Exception:
        pass

    return result


async def _get_knowledge_triples() -> dict:
    """Get knowledge graph triples."""
    # TODO: Implement when knowledge service is wired up
    return {
        "triples": [],
        "count": 0,
        "message": "Knowledge service not yet integrated with MCP",
    }


def main() -> None:
    """Entry point for running the server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
