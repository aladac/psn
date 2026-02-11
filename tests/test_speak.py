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

    def test_get_sample_rate_returns_fallback(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        mock_voice.synthesize.return_value = iter([])
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

    @patch("personality.speak.sd")
    def test_say_synthesizes_and_plays(self, mock_sd: MagicMock, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        mock_voice = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.sample_rate = 22050
        mock_chunk.audio_int16_bytes = b"\x00\x01\x02\x03"
        mock_voice.synthesize.return_value = [mock_chunk]

        with patch.object(speaker, "_load_voice", return_value=mock_voice):
            speaker.say("hello", "voice")

        mock_sd.play.assert_called_once()
        mock_sd.wait.assert_called_once()

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


class TestSpeakStop:
    """Tests for Speak.stop() static method."""

    @patch("personality.speak.sd")
    def test_stop_calls_sd_stop(self, mock_sd: MagicMock) -> None:
        mock_sd.get_stream.return_value = None
        result = Speak.stop()
        mock_sd.stop.assert_called()
        assert result is False

    @patch("personality.speak.sd")
    def test_stop_returns_true_when_active(self, mock_sd: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_stream.active = True
        mock_sd.get_stream.return_value = mock_stream
        result = Speak.stop()
        assert result is True

    @patch("personality.speak.sd")
    def test_stop_handles_exception(self, mock_sd: MagicMock) -> None:
        mock_sd.get_stream.side_effect = Exception("test error")
        result = Speak.stop()
        mock_sd.stop.assert_called()
        assert result is False
