"""Voice synthesis using Piper TTS with sounddevice playback."""

import logging
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice

logger = logging.getLogger(__name__)

SAMPLE_WIDTH = 2  # 16-bit audio
CHANNELS = 1  # Mono


class Speak:
    """Piper TTS voice synthesizer with in-process audio playback."""

    def __init__(self, voice_dir: Path) -> None:
        """Initialize with voice directory.

        Args:
            voice_dir: Directory containing .onnx and .onnx.json voice files.
        """
        self.voice_dir = voice_dir
        self._cache: dict[str, PiperVoice] = {}

    def say(self, text: str, voice: str) -> None:
        """Synthesize and play text.

        Args:
            text: Text to speak.
            voice: Voice model name (without extension).

        Raises:
            FileNotFoundError: If voice model not found.
        """
        piper_voice = self._load_voice(voice)
        sample_rate = self._get_sample_rate(piper_voice, text)
        audio_bytes = self._collect_audio(piper_voice, text)

        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        sd.play(audio_array, samplerate=sample_rate)
        sd.wait()

    def save(self, text: str, voice: str, output_path: Path) -> None:
        """Synthesize text and save to WAV file.

        Args:
            text: Text to speak.
            voice: Voice model name (without extension).
            output_path: Path to save WAV file.

        Raises:
            FileNotFoundError: If voice model not found.
        """
        piper_voice = self._load_voice(voice)
        sample_rate = self._get_sample_rate(piper_voice, text)
        audio_bytes = self._collect_audio(piper_voice, text)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_bytes)

    @staticmethod
    def stop() -> bool:
        """Stop any currently playing audio. Returns True if audio was playing."""
        try:
            status = sd.get_stream()
            if status and status.active:
                sd.stop()
                logger.info("Stopped active playback")
                return True
        except Exception:
            pass
        sd.stop()
        return False

    def _load_voice(self, voice: str) -> PiperVoice:
        """Load and cache voice model."""
        if voice in self._cache:
            return self._cache[voice]

        model_path = self.voice_dir / f"{voice}.onnx"
        config_path = self.voice_dir / f"{voice}.onnx.json"

        if not model_path.exists():
            raise FileNotFoundError(f"Voice model not found: {model_path}")
        if not config_path.exists():
            raise FileNotFoundError(f"Voice config not found: {config_path}")

        logger.debug("Loading voice: %s", voice)
        piper_voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        self._cache[voice] = piper_voice
        return piper_voice

    def _collect_audio(self, piper_voice: PiperVoice, text: str) -> bytes:
        """Collect audio chunks from synthesizer."""
        audio_bytes = b""
        for chunk in piper_voice.synthesize(text):
            audio_bytes += chunk.audio_int16_bytes
        return audio_bytes

    def _get_sample_rate(self, piper_voice: PiperVoice, text: str) -> int:
        """Get sample rate from first audio chunk."""
        for chunk in piper_voice.synthesize(text[:10]):
            return chunk.sample_rate
        return 22050  # Default fallback
