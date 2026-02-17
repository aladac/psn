#!/usr/bin/env python3
"""TTS MCP Server.

Provides text-to-speech capabilities using piper-tts Python library.
"""
import io
import json
import logging
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("tts")

# Default voice model
DEFAULT_VOICE = "en_US-lessac-medium"
PIPER_DATA_DIR = Path.home() / ".local" / "share" / "piper-tts"

# Lazy-loaded piper components
_piper_voice = None


def get_piper_voice(voice_name: str | None = None):
    """Get or create piper voice instance."""
    global _piper_voice

    voice = voice_name or DEFAULT_VOICE
    voices_dir = PIPER_DATA_DIR / "voices"
    model_path = voices_dir / f"{voice}.onnx"
    config_path = voices_dir / f"{voice}.onnx.json"

    if not model_path.exists():
        return None, f"Voice model not found: {model_path}"

    try:
        from piper import PiperVoice

        _piper_voice = PiperVoice.load(str(model_path), str(config_path))
        return _piper_voice, None
    except ImportError:
        return None, "piper-tts not installed. Run: pip install piper-tts"
    except Exception as e:
        return None, str(e)


def list_voices() -> list[dict[str, str]]:
    """List available piper voices."""
    voices_dir = PIPER_DATA_DIR / "voices"
    if not voices_dir.exists():
        return []

    voices = []
    for onnx_file in voices_dir.glob("*.onnx"):
        voice_name = onnx_file.stem
        voices.append({"name": voice_name, "path": str(onnx_file)})

    return voices


def speak_text(text: str, voice: str | None = None) -> dict[str, Any]:
    """Generate speech from text and play it."""
    piper_voice, error = get_piper_voice(voice)
    if error:
        return {"success": False, "error": error}

    try:
        # Generate audio to WAV bytes
        audio_buffer = io.BytesIO()

        with wave.open(audio_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(piper_voice.config.sample_rate)

            for chunk in piper_voice.synthesize(text):
                wav_file.writeframes(chunk.audio_int16_bytes)

        # Write to temp file and play (macOS)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_buffer.getvalue())
            tmp_path = tmp_file.name

        # Play audio using afplay (macOS)
        subprocess.run(["afplay", tmp_path], timeout=120, check=True)

        # Clean up
        Path(tmp_path).unlink(missing_ok=True)

        return {"success": True, "text": text[:100] + "..." if len(text) > 100 else text}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Playback timed out"}
    except Exception as e:
        logger.exception("TTS error")
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
            "voices_dir": str(PIPER_DATA_DIR / "voices"),
        }

    elif name == "set_voice":
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
