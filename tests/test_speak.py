"""Tests for personality.speak module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from personality.speak import Speak


class TestSpeak:
    """Tests for Speak class."""

    def test_init_stores_voice_dir(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        assert speaker.voice_dir == tmp_path

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

    def test_play_raises_when_no_player_available(self, tmp_path: Path) -> None:
        speaker = Speak(tmp_path)
        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(RuntimeError, match="No audio player found"),
        ):
            speaker._play(b"fake wav data")
