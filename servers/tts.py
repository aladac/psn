#!/usr/bin/env python3
"""TTS MCP Server.

Provides text-to-speech capabilities using piper-tts.
"""
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("tts")

# Default voice model
DEFAULT_VOICE = os.environ.get("PIPER_VOICE", "en_US-lessac-medium")
PIPER_DATA_DIR = Path.home() / ".local" / "share" / "piper-tts"


def ensure_piper() -> bool:
    """Check if piper is installed."""
    try:
        result = subprocess.run(["piper", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def list_voices() -> list[dict[str, str]]:
    """List available piper voices."""
    voices_dir = PIPER_DATA_DIR / "voices"
    if not voices_dir.exists():
        return []

    voices = []
    for onnx_file in voices_dir.rglob("*.onnx"):
        voice_name = onnx_file.stem
        voices.append({"name": voice_name, "path": str(onnx_file)})

    return voices


def speak_text(text: str, voice: str | None = None) -> dict[str, Any]:
    """Generate speech from text and play it."""
    if not ensure_piper():
        return {"success": False, "error": "piper is not installed"}

    voice_model = voice or DEFAULT_VOICE
    voices_dir = PIPER_DATA_DIR / "voices"

    # Find voice model file
    voice_path = None
    for onnx_file in voices_dir.rglob("*.onnx"):
        if voice_model in str(onnx_file):
            voice_path = str(onnx_file)
            break

    if not voice_path:
        return {"success": False, "error": f"Voice not found: {voice_model}"}

    try:
        # Generate speech to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        # Run piper
        piper_cmd = ["piper", "--model", voice_path, "--output_file", tmp_path]
        result = subprocess.run(
            piper_cmd,
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        # Play the audio (macOS)
        play_cmd = ["afplay", tmp_path]
        subprocess.run(play_cmd, timeout=120)

        # Clean up
        os.unlink(tmp_path)

        return {"success": True, "text": text[:100] + "..." if len(text) > 100 else text}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Speech generation timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available TTS tools."""
    return [
        Tool(
            name="speak",
            description="Convert text to speech and play it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak"},
                    "voice": {"type": "string", "description": "Voice model to use"},
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="voices",
            description="List available voice models.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="set_voice",
            description="Set the default voice model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "voice": {"type": "string", "description": "Voice model name"},
                },
                "required": ["voice"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    global DEFAULT_VOICE
    logger.info(f"Tool called: {name} with {arguments}")

    if name == "speak":
        result = speak_text(arguments["text"], arguments.get("voice"))

    elif name == "voices":
        voices = list_voices()
        result = {
            "success": True,
            "voices": voices,
            "default": DEFAULT_VOICE,
            "piper_installed": ensure_piper(),
        }

    elif name == "set_voice":
        # This would persist to a config file in a full implementation
        DEFAULT_VOICE = arguments["voice"]
        result = {"success": True, "voice": DEFAULT_VOICE}

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
