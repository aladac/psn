"""TTS CLI commands."""

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from personality.services.cart_registry import CartRegistry

app = typer.Typer(invoke_without_command=True)
console = Console()

# Voice directories (local plugin dir + system piper dir)
LOCAL_VOICES_DIR = Path(__file__).parent.parent.parent.parent / "voices"
PIPER_DATA_DIR = Path.home() / ".local" / "share" / "piper-tts"
SYSTEM_VOICES_DIR = PIPER_DATA_DIR / "voices"
DEFAULT_VOICE = "en_US-lessac-medium"

# Character voice sources (HuggingFace)
CHARACTER_VOICES = {
    "bt7274": {
        "name": "BT-7274",
        "source": "local",  # Already in voices/
        "file": "BT7274",
    },
    "glados": {
        "name": "GLaDOS",
        "source": "https://huggingface.co/datasets/GLaDOS/glados-tts",
        "note": "Requires manual download - see doc/tts-voices.md",
    },
    "hal9000": {
        "name": "HAL 9000",
        "source": "custom",
        "note": "No public model available yet",
    },
    "jarvis": {
        "name": "JARVIS",
        "source": "custom",
        "note": "No public model available yet",
    },
}


def find_voice_path(voice: str) -> Path | None:
    """Find a voice model in local or system directories."""
    # Check local voices first (character voices)
    local_path = LOCAL_VOICES_DIR / f"{voice}.onnx"
    if local_path.exists():
        return local_path

    # Check system piper voices
    system_path = SYSTEM_VOICES_DIR / f"{voice}.onnx"
    if system_path.exists():
        return system_path

    return None


def list_all_voices() -> list[tuple[str, Path, str]]:
    """List all available voices from all directories."""
    voices: list[tuple[str, Path, str]] = []

    # Local character voices
    if LOCAL_VOICES_DIR.exists():
        for voice_path in LOCAL_VOICES_DIR.glob("*.onnx"):
            voices.append((voice_path.stem, voice_path, "character"))

    # System piper voices
    if SYSTEM_VOICES_DIR.exists():
        for voice_path in SYSTEM_VOICES_DIR.glob("*.onnx"):
            if voice_path.stem not in [v[0] for v in voices]:
                voices.append((voice_path.stem, voice_path, "piper"))

    return sorted(voices, key=lambda x: x[0].lower())


def get_active_voice() -> str:
    """Get the active persona's voice or default."""
    try:
        registry = CartRegistry()
        cart = registry.get_active()
        if cart and cart.voice:
            return cart.voice
    except Exception:
        pass
    return DEFAULT_VOICE


@app.callback(invoke_without_command=True)
def tts_main(ctx: typer.Context) -> None:
    """Text-to-speech commands."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("speak")
def speak(
    text: str = typer.Argument(..., help="Text to speak"),
    voice: str = typer.Option(None, "--voice", "-v", help="Voice model (default: active persona's voice)"),
) -> None:
    """Speak text aloud using active persona's voice."""
    if voice is None:
        voice = get_active_voice()

    try:
        import tempfile
        import wave

        from piper import PiperVoice

        model_path = find_voice_path(voice)
        if model_path is None:
            console.print(f"[red]Voice not found: {voice}[/red]")
            available = [v[0] for v in list_all_voices()]
            if available:
                console.print(f"Available: {', '.join(available[:5])}")
            raise typer.Exit(1)

        config_path = model_path.with_suffix(".onnx.json")

        piper_voice = PiperVoice.load(str(model_path), str(config_path))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wav_file:
                piper_voice.synthesize_wav(text, wav_file)

        subprocess.run(["afplay", tmp_path], timeout=120, check=True)
        Path(tmp_path).unlink(missing_ok=True)

    except ImportError:
        console.print("[red]piper-tts not installed[/red]")
        console.print("Run: pip install piper-tts")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("voices")
def list_voices() -> None:
    """List available voice models."""
    voices = list_all_voices()

    if not voices:
        console.print("[dim]No voices installed[/dim]")
        console.print("\nDownload a voice:")
        console.print("  psn tts download en_US-lessac-medium")
        return

    table = Table(title="Installed Voices")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Size", justify="right")

    for name, path, voice_type in voices:
        size_mb = path.stat().st_size / (1024 * 1024)
        type_display = "[green]character[/green]" if voice_type == "character" else "piper"
        table.add_row(name, type_display, f"{size_mb:.1f} MB")

    console.print(table)
    console.print(f"\n[dim]Locations: {LOCAL_VOICES_DIR}, {SYSTEM_VOICES_DIR}[/dim]")


@app.command("download")
def download_voice(
    voice: str = typer.Argument(..., help="Voice name (e.g., en_US-lessac-medium)"),
) -> None:
    """Download a piper voice model."""
    SYSTEM_VOICES_DIR.mkdir(parents=True, exist_ok=True)

    model_path = SYSTEM_VOICES_DIR / f"{voice}.onnx"
    config_path = SYSTEM_VOICES_DIR / f"{voice}.onnx.json"

    if model_path.exists():
        console.print(f"[yellow]Voice already exists: {voice}[/yellow]")
        return

    # Piper voices URL pattern
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

    # Parse voice name: lang_REGION-name-quality
    parts = voice.split("-")
    if len(parts) >= 2:
        lang = parts[0]  # e.g., en_US
        lang_short = lang.split("_")[0]  # e.g., en
        name = parts[1]  # e.g., lessac
        quality = parts[2] if len(parts) > 2 else "medium"

        model_url = f"{base_url}/{lang_short}/{lang}/{name}/{quality}/{voice}.onnx"
        config_url = f"{base_url}/{lang_short}/{lang}/{name}/{quality}/{voice}.onnx.json"
    else:
        console.print(f"[red]Invalid voice format: {voice}[/red]")
        console.print("Expected: lang_REGION-name-quality (e.g., en_US-lessac-medium)")
        raise typer.Exit(1)

    console.print(f"Downloading {voice}...")

    try:
        import urllib.request

        console.print(f"  [dim]{model_url}[/dim]")
        urllib.request.urlretrieve(model_url, model_path)
        console.print("  [green]✓[/green] Model downloaded")

        urllib.request.urlretrieve(config_url, config_path)
        console.print("  [green]✓[/green] Config downloaded")

        size_mb = model_path.stat().st_size / (1024 * 1024)
        console.print(f"\n[green]Installed:[/green] {voice} ({size_mb:.1f} MB)")

    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        model_path.unlink(missing_ok=True)
        config_path.unlink(missing_ok=True)
        raise typer.Exit(1) from None


@app.command("test")
def test_voice(
    voice: str = typer.Option(None, "--voice", "-v", help="Voice to test (default: active persona's voice)"),
) -> None:
    """Test a voice with sample text."""
    if voice is None:
        voice = get_active_voice()
    speak("Hello! This is a test of the text to speech system.", voice)


@app.command("current")
def show_current() -> None:
    """Show the current TTS voice from active persona."""
    try:
        registry = CartRegistry()
        cart = registry.get_active()

        if cart:
            console.print(f"[bold]Active Persona:[/bold] {cart.tag}")
            if cart.voice:
                console.print(f"[bold]Voice:[/bold] {cart.voice}")
                # Check if voice is installed (in either directory)
                voice_path = find_voice_path(cart.voice)
                if voice_path:
                    console.print(f"[green]✓[/green] Voice installed at {voice_path.parent.name}/")
                else:
                    console.print("[yellow]![/yellow] Voice not installed")
                    console.print(f"  Run: psn tts download {cart.voice}")
            else:
                console.print(f"[dim]No voice configured, using default: {DEFAULT_VOICE}[/dim]")

            if cart.preferences.tts.enabled:
                console.print("[green]TTS Enabled[/green]")
            else:
                console.print("[dim]TTS Disabled[/dim]")
        else:
            console.print("[yellow]No active persona[/yellow]")
            console.print(f"[dim]Using default voice: {DEFAULT_VOICE}[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("characters")
def list_character_voices() -> None:
    """List available character voices."""
    table = Table(title="Character Voices")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Notes", style="dim")

    for char_id, info in CHARACTER_VOICES.items():
        if info.get("source") == "local":
            voice_path = find_voice_path(info.get("file", char_id))
            status = "[green]installed[/green]" if voice_path else "[yellow]not found[/yellow]"
        else:
            status = "[dim]manual[/dim]"

        table.add_row(
            char_id,
            info["name"],
            status,
            info.get("note", ""),
        )

    console.print(table)
