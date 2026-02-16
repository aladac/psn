"""TTS CLI commands."""

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(invoke_without_command=True)
console = Console()

PIPER_DATA_DIR = Path.home() / ".local" / "share" / "piper-tts"
VOICES_DIR = PIPER_DATA_DIR / "voices"


@app.callback(invoke_without_command=True)
def tts_main(ctx: typer.Context) -> None:
    """Text-to-speech commands."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("speak")
def speak(
    text: str = typer.Argument(..., help="Text to speak"),
    voice: str = typer.Option("en_US-lessac-medium", "--voice", "-v", help="Voice model"),
) -> None:
    """Speak text aloud."""
    try:
        from piper import PiperVoice
        import io
        import wave
        import tempfile

        model_path = VOICES_DIR / f"{voice}.onnx"
        config_path = VOICES_DIR / f"{voice}.onnx.json"

        if not model_path.exists():
            console.print(f"[red]Voice not found: {voice}[/red]")
            console.print(f"Available: {', '.join(v.stem for v in VOICES_DIR.glob('*.onnx'))}")
            raise typer.Exit(1)

        piper_voice = PiperVoice.load(str(model_path), str(config_path))

        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(piper_voice.config.sample_rate)
            for audio_bytes in piper_voice.synthesize_stream_raw(text):
                wav_file.writeframes(audio_bytes)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_buffer.getvalue())
            tmp_path = tmp.name

        subprocess.run(["afplay", tmp_path], timeout=120, check=True)
        Path(tmp_path).unlink(missing_ok=True)

    except ImportError:
        console.print("[red]piper-tts not installed[/red]")
        console.print("Run: pip install piper-tts")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("voices")
def list_voices() -> None:
    """List available voice models."""
    if not VOICES_DIR.exists():
        console.print(f"[yellow]No voices directory: {VOICES_DIR}[/yellow]")
        return

    voices = list(VOICES_DIR.glob("*.onnx"))
    if not voices:
        console.print("[dim]No voices installed[/dim]")
        return

    table = Table(title="Installed Voices")
    table.add_column("Name", style="cyan")
    table.add_column("Size", justify="right")

    for voice in sorted(voices):
        size_mb = voice.stat().st_size / (1024 * 1024)
        table.add_row(voice.stem, f"{size_mb:.1f} MB")

    console.print(table)
    console.print(f"\n[dim]Location: {VOICES_DIR}[/dim]")


@app.command("download")
def download_voice(
    voice: str = typer.Argument(..., help="Voice name (e.g., en_US-lessac-medium)"),
) -> None:
    """Download a piper voice model."""
    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    model_path = VOICES_DIR / f"{voice}.onnx"
    config_path = VOICES_DIR / f"{voice}.onnx.json"

    if model_path.exists():
        console.print(f"[yellow]Voice already exists: {voice}[/yellow]")
        return

    # Piper voices URL pattern
    base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main"
    
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
        console.print(f"  [green]✓[/green] Model downloaded")

        urllib.request.urlretrieve(config_url, config_path)
        console.print(f"  [green]✓[/green] Config downloaded")

        size_mb = model_path.stat().st_size / (1024 * 1024)
        console.print(f"\n[green]Installed:[/green] {voice} ({size_mb:.1f} MB)")

    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        model_path.unlink(missing_ok=True)
        config_path.unlink(missing_ok=True)
        raise typer.Exit(1)


@app.command("test")
def test_voice(
    voice: str = typer.Option("en_US-lessac-medium", "--voice", "-v", help="Voice to test"),
) -> None:
    """Test a voice with sample text."""
    speak("Hello! This is a test of the text to speech system.", voice)
