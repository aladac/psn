"""Tests for personality.speak module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personality.speak import Speak


class TestSpeak:
    """Tests for Speak class."""

    def test_init_stores_voice_dir(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        assert speaker.voice_dir == tmp_path

    def test_init_creates_empty_cache(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        assert speaker._cache == {}

    def test_load_voice_raises_when_model_not_found(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        with pytest.raises(FileNotFoundError, match="Voice model not found"):
            speaker._load_voice("nonexistent")

    def test_load_voice_raises_when_config_not_found(self, tmp_path: Path) -> None:
        # Create model file but no config
        (tmp_path / "test.onnx").touch()
        speaker = Speak(tmp_path)
        with pytest.raises(FileNotFoundError, match="Voice config not found"):
            speaker._load_voice("test")

    def test_load_voice_caches_result(self, tmp_path: Path) -> None:
        (tmp_path / "test.onnx").touch()
        (tmp_path / "test.onnx.json").touch()
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        with patch("personality.speak.PiperVoice.load", return_value=mock_voice):
            voice1 = speaker._load_voice("test")
            voice2 = speaker._load_voice("test")
        assert voice1 is voice2
        assert "test" in speaker._cache

    def test_play_raises_when_no_player_available(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(RuntimeError, match="No audio player found"),
        ):
            speaker._play(b"fake wav data")

    def test_play_succeeds_with_first_player(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            speaker._play(b"fake wav data")

    def test_play_tries_next_player_on_failure(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError()
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=mock_run):
            speaker._play(b"fake wav data")
        assert call_count == 2

    def test_get_sample_rate_returns_fallback(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        mock_voice.synthesize.return_value = iter([])  # Empty iterator
        result = speaker._get_sample_rate(mock_voice, "test")
        assert result == 22050

    def test_get_sample_rate_from_chunk(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.sample_rate = 44100
        mock_voice.synthesize.return_value = iter([mock_chunk])
        result = speaker._get_sample_rate(mock_voice, "test")
        assert result == 44100

    def test_collect_audio_concatenates_chunks(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        chunk1 = MagicMock()
        chunk1.audio_int16_bytes = b"chunk1"
        chunk2 = MagicMock()
        chunk2.audio_int16_bytes = b"chunk2"
        mock_voice.synthesize.return_value = [chunk1, chunk2]
        result = speaker._collect_audio(mock_voice, "test")
        assert result == b"chunk1chunk2"

    def test_say_synthesizes_and_plays(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        with (
            patch.object(speaker, "_synthesize", return_value=b"wav data") as mock_synth,
            patch.object(speaker, "_play") as mock_play,
        ):
            speaker.say("hello", "voice")
        mock_synth.assert_called_once_with("hello", "voice")
        mock_play.assert_called_once_with(b"wav data")

    def test_save_writes_wav_file(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        output_file = tmp_path / "output.wav"
        mock_voice = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.sample_rate = 22050
        mock_chunk.audio_int16_bytes = b"\x00\x01\x02\x03"
        mock_voice.synthesize.return_value = [mock_chunk]
        with patch.object(speaker, "_load_voice", return_value=mock_voice):
            speaker.save("hello", "voice", output_file)
        assert output_file.exists()

    def test_synthesize_returns_wav_bytes(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.sample_rate = 22050
        mock_chunk.audio_int16_bytes = b"\x00\x01"
        mock_voice.synthesize.return_value = [mock_chunk]
        with patch.object(speaker, "_load_voice", return_value=mock_voice):
            result = speaker._synthesize("hello", "voice")
        assert isinstance(result, bytes)
        assert len(result) > 0
        # WAV files start with RIFF header
        assert result[:4] == b"RIFF"
