"""Tests for personality.hooks module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from personality.hooks import (
    DEFAULT_CART,
    HookResult,
    get_speaker,
    log_hook,
    notify,
    read_stdin_json,
    session_end,
    session_start,
    stop,
)


class TestHookResult:
    """Tests for HookResult dataclass."""

    def test_to_json_minimal(self) -> None:
        result = HookResult(status="ok")
        parsed = json.loads(result.to_json())
        assert parsed == {"status": "ok"}

    def test_to_json_with_message(self) -> None:
        result = HookResult(status="error", message="Something failed")
        parsed = json.loads(result.to_json())
        assert parsed == {"status": "error", "message": "Something failed"}

    def test_to_json_with_data(self) -> None:
        result = HookResult(status="ok", data={"count": 5})
        parsed = json.loads(result.to_json())
        assert parsed == {"status": "ok", "count": 5}


class TestLogHook:
    """Tests for log_hook function."""

    def test_creates_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "hooks.log"
            with patch("personality.hooks.HOOKS_LOG", log_path):
                log_hook("test", "test message")
            assert log_path.exists()
            content = log_path.read_text()
            assert "[test]" in content
            assert "test message" in content

    def test_appends_to_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "hooks.log"
            with patch("personality.hooks.HOOKS_LOG", log_path):
                log_hook("first", "message1")
                log_hook("second", "message2")
            content = log_path.read_text()
            assert "[first]" in content
            assert "[second]" in content


class TestReadStdinJson:
    """Tests for read_stdin_json function."""

    def test_returns_empty_when_tty(self) -> None:
        with patch("sys.stdin.isatty", return_value=True):
            result = read_stdin_json()
        assert result == {}

    def test_parses_json_from_stdin(self) -> None:
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stdin.read", return_value='{"key": "value"}'),
        ):
            result = read_stdin_json()
        assert result == {"key": "value"}

    def test_returns_empty_on_invalid_json(self) -> None:
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stdin.read", return_value="not json"),
        ):
            result = read_stdin_json()
        assert result == {}


class TestGetSpeaker:
    """Tests for get_speaker function."""

    def test_returns_none_when_cart_not_found(self) -> None:
        with patch("personality.hooks.load_cart", return_value=None):
            speaker, voice = get_speaker("nonexistent")
        assert speaker is None
        assert voice is None

    def test_returns_speaker_and_voice(self) -> None:
        cart_data = {"preferences": {"speak": {"voice": "test_voice"}}}
        with (
            patch("personality.hooks.load_cart", return_value=cart_data),
            patch("personality.hooks.get_cart_voice", return_value="test_voice"),
        ):
            speaker, voice = get_speaker("test")
        assert speaker is not None
        assert voice == "test_voice"


class TestSessionStart:
    """Tests for session_start hook."""

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.get_speaker")
    @patch("personality.hooks.load_cart")
    def test_returns_ok_with_persona(
        self,
        mock_load: MagicMock,
        mock_speaker: MagicMock,
        mock_log: MagicMock,
    ) -> None:
        mock_load.return_value = {"preferences": {"identity": {"name": "BT-7274", "tagline": "Protocol 3"}}}
        mock_speaker.return_value = (MagicMock(), "bt7274")

        result = session_start("bt7274")

        assert result.status == "ok"
        assert result.data["persona"] == "BT-7274"
        assert result.data["greeting"] == "Protocol 3"

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.load_cart")
    def test_returns_error_when_cart_not_found(self, mock_load: MagicMock, mock_log: MagicMock) -> None:
        mock_load.return_value = None
        result = session_start("nonexistent")
        assert result.status == "error"


class TestSessionEnd:
    """Tests for session_end hook."""

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.get_speaker")
    def test_returns_consolidated_count(self, mock_speaker: MagicMock, mock_log: MagicMock) -> None:
        mock_speaker.return_value = (MagicMock(), "test")
        result = session_end("test")
        assert result.status == "ok"
        assert "consolidated" in result.data


class TestStop:
    """Tests for stop hook."""

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.read_stdin_json")
    @patch("personality.hooks.get_speaker")
    def test_speaks_on_end_turn(
        self,
        mock_speaker: MagicMock,
        mock_stdin: MagicMock,
        mock_log: MagicMock,
    ) -> None:
        mock_stdin.return_value = {"stop_reason": "end_turn"}
        mock_speak = MagicMock()
        mock_speaker.return_value = (mock_speak, "test")

        result = stop("test")

        assert result.status == "ok"
        mock_speak.say.assert_called_once()

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.read_stdin_json")
    @patch("personality.hooks.get_speaker")
    def test_silent_on_tool_use(
        self,
        mock_speaker: MagicMock,
        mock_stdin: MagicMock,
        mock_log: MagicMock,
    ) -> None:
        mock_stdin.return_value = {"stop_reason": "tool_use"}
        mock_speak = MagicMock()
        mock_speaker.return_value = (mock_speak, "test")

        result = stop("test")

        assert result.status == "ok"
        mock_speak.say.assert_not_called()


class TestNotify:
    """Tests for notify hook."""

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.read_stdin_json")
    @patch("personality.hooks.get_speaker")
    def test_speaks_message_from_arg(
        self,
        mock_speaker: MagicMock,
        mock_stdin: MagicMock,
        mock_log: MagicMock,
    ) -> None:
        mock_stdin.return_value = {}
        mock_speak = MagicMock()
        mock_speaker.return_value = (mock_speak, "test")

        result = notify("test", message="Hello Pilot")

        assert result.status == "ok"
        mock_speak.say.assert_called_with("Hello Pilot", "test")

    @patch("personality.hooks.log_hook")
    @patch("personality.hooks.read_stdin_json")
    @patch("personality.hooks.get_speaker")
    def test_speaks_message_from_stdin(
        self,
        mock_speaker: MagicMock,
        mock_stdin: MagicMock,
        mock_log: MagicMock,
    ) -> None:
        mock_stdin.return_value = {"title": "Notification Title"}
        mock_speak = MagicMock()
        mock_speaker.return_value = (mock_speak, "test")

        result = notify("test")

        assert result.status == "ok"
        mock_speak.say.assert_called_with("Notification Title", "test")


class TestConstants:
    """Tests for module constants."""

    def test_default_cart(self) -> None:
        assert DEFAULT_CART == "bt7274"
