"""Tests for personality.cli module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from personality.cli import _resolve_text, main


class TestResolveText:
    """Tests for _resolve_text helper function."""

    def test_returns_text_argument_when_provided(self) -> None:
        result = _resolve_text("hello", None)
        assert result == "hello"

    def test_reads_from_file_when_input_file_provided(self, tmp_path: Path) -> None:
        input_file = tmp_path / "input.txt"
        input_file.write_text("  from file  \n")
        result = _resolve_text(None, str(input_file))
        assert result == "from file"

    def test_text_takes_precedence_over_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "input.txt"
        input_file.write_text("from file")
        result = _resolve_text("from arg", str(input_file))
        assert result == "from arg"

    def test_returns_empty_string_when_no_input(self) -> None:
        with patch("sys.stdin.isatty", return_value=True):
            result = _resolve_text(None, None)
        assert result == ""


class TestMainCommand:
    """Tests for main CLI group."""

    def test_shows_help_when_no_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert "Personality engine CLI" in result.output

    def test_shows_version_with_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "psn v" in result.output


class TestSpeakCommand:
    """Tests for speak command."""

    def test_error_when_no_text_provided(self) -> None:
        runner = CliRunner()
        with patch("sys.stdin.isatty", return_value=True):
            result = runner.invoke(main, ["speak"])
        assert result.exit_code == 1
        assert "No text provided" in result.output

    def test_error_when_cart_not_found(self) -> None:
        runner = CliRunner()
        with (
            patch("personality.cli.load_cart", return_value=None),
            patch("personality.cli.list_carts", return_value=["other"]),
        ):
            result = runner.invoke(main, ["speak", "hello", "-c", "missing"])
        assert result.exit_code == 1
        assert "Cart not found" in result.output

    def test_speaks_text_successfully(self) -> None:
        runner = CliRunner()
        mock_speaker = MagicMock()
        with (
            patch("personality.cli.load_cart", return_value={"preferences": {}}),
            patch("personality.cli.Speak", return_value=mock_speaker),
        ):
            result = runner.invoke(main, ["speak", "hello", "-c", "test"])
        assert result.exit_code == 0
        mock_speaker.say.assert_called_once_with("hello", "test")

    def test_saves_to_output_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        output_file = tmp_path / "output.wav"
        mock_speaker = MagicMock()
        with (
            patch("personality.cli.load_cart", return_value={"preferences": {}}),
            patch("personality.cli.Speak", return_value=mock_speaker),
        ):
            result = runner.invoke(main, ["speak", "hello", "-c", "test", "-o", str(output_file)])
        assert result.exit_code == 0
        assert "Audio saved" in result.output
        mock_speaker.save.assert_called_once()

    def test_handles_voice_not_found(self) -> None:
        runner = CliRunner()
        mock_speaker = MagicMock()
        mock_speaker.say.side_effect = FileNotFoundError("Voice not found")
        with (
            patch("personality.cli.load_cart", return_value={"preferences": {}}),
            patch("personality.cli.Speak", return_value=mock_speaker),
        ):
            result = runner.invoke(main, ["speak", "hello", "-c", "test"])
        assert result.exit_code == 1
        assert "Error:" in result.output

    def test_handles_playback_error(self) -> None:
        runner = CliRunner()
        mock_speaker = MagicMock()
        mock_speaker.say.side_effect = RuntimeError("No player")
        with (
            patch("personality.cli.load_cart", return_value={"preferences": {}}),
            patch("personality.cli.Speak", return_value=mock_speaker),
        ):
            result = runner.invoke(main, ["speak", "hello", "-c", "test"])
        assert result.exit_code == 1
        assert "Playback error" in result.output


class TestCartsCommand:
    """Tests for carts command."""

    def test_shows_no_carts_message(self) -> None:
        runner = CliRunner()
        with patch("personality.cli.list_carts", return_value=[]):
            result = runner.invoke(main, ["carts"])
        assert result.exit_code == 0
        assert "No carts found" in result.output

    def test_lists_available_carts(self) -> None:
        runner = CliRunner()
        cart_data = {"preferences": {"identity": {"name": "Test"}, "speak": {"voice": "v1"}}}
        with (
            patch("personality.cli.list_carts", return_value=["test"]),
            patch("personality.cli.load_cart", return_value=cart_data),
        ):
            result = runner.invoke(main, ["carts"])
        assert result.exit_code == 0
        assert "test" in result.output


class TestVoicesCommand:
    """Tests for voices command."""

    def test_shows_no_directory_message(self, tmp_path: Path) -> None:
        runner = CliRunner()
        missing = tmp_path / "missing"
        with patch("personality.cli.DEFAULT_VOICE_DIR", missing):
            result = runner.invoke(main, ["voices"])
        assert result.exit_code == 0
        assert "Voice directory not found" in result.output

    def test_shows_no_voices_message(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("personality.cli.DEFAULT_VOICE_DIR", tmp_path):
            result = runner.invoke(main, ["voices"])
        assert result.exit_code == 0
        assert "No voice models found" in result.output

    def test_lists_available_voices(self, tmp_path: Path) -> None:
        runner = CliRunner()
        (tmp_path / "voice1.onnx").touch()
        (tmp_path / "voice1.onnx.json").touch()
        with patch("personality.cli.DEFAULT_VOICE_DIR", tmp_path):
            result = runner.invoke(main, ["voices"])
        assert result.exit_code == 0
        assert "voice1" in result.output


class TestInstallCommand:
    """Tests for install command."""

    def test_installs_commands(self, tmp_path: Path) -> None:
        runner = CliRunner()
        # Create mock commands directory in package
        mock_cmd = MagicMock()
        mock_cmd.name = "speak.md"
        mock_cmd.read_text.return_value = "# Speak"

        mock_commands_path = MagicMock()
        mock_commands_path.iterdir.return_value = [mock_cmd]

        mock_files = MagicMock()
        mock_files.return_value.__truediv__.return_value = mock_commands_path

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("importlib.resources.files", mock_files),
        ):
            result = runner.invoke(main, ["install"])
        assert result.exit_code == 0
        assert "Installed" in result.output or "Commands installed" in result.output

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        runner = CliRunner()
        target_dir = tmp_path / ".claude" / "commands" / "psn"
        target_dir.mkdir(parents=True)
        (target_dir / "speak.md").touch()

        mock_cmd = MagicMock()
        mock_cmd.name = "speak.md"

        mock_commands_path = MagicMock()
        mock_commands_path.iterdir.return_value = [mock_cmd]

        mock_files = MagicMock()
        mock_files.return_value.__truediv__.return_value = mock_commands_path

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("importlib.resources.files", mock_files),
        ):
            result = runner.invoke(main, ["install"])
        assert result.exit_code == 0
        assert "Skipped" in result.output


class TestMcpCommand:
    """Tests for mcp command."""

    def test_sets_cart_env_and_runs_server(self) -> None:
        runner = CliRunner()
        with patch("personality.mcp.run_server") as mock_run:
            result = runner.invoke(main, ["mcp", "-c", "test_cart"])
        assert result.exit_code == 0
        mock_run.assert_called_once()


class TestUninstallCommand:
    """Tests for uninstall command."""

    def test_removes_commands_directory(self, tmp_path: Path) -> None:
        runner = CliRunner()
        target_dir = tmp_path / ".claude" / "commands" / "psn"
        target_dir.mkdir(parents=True)
        (target_dir / "speak.md").touch()
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(main, ["uninstall"])
        assert result.exit_code == 0
        assert "Removed" in result.output
        assert not target_dir.exists()

    def test_handles_no_commands_installed(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(main, ["uninstall"])
        assert result.exit_code == 0
        assert "No commands installed" in result.output


class TestIndexCommand:
    """Tests for index command."""

    def test_index_shows_status(self, tmp_path: Path) -> None:
        runner = CliRunner()
        mock_indexer = MagicMock()
        mock_indexer.status.return_value = {
            "project_path": str(tmp_path),
            "db_path": str(tmp_path / "test.db"),
            "file_count": 5,
            "chunk_count": 20,
            "has_summary": False,
        }

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = runner.invoke(main, ["index", "--status"])

        assert result.exit_code == 0
        assert "Files:" in result.output
        mock_indexer.close.assert_called_once()

    def test_index_runs_indexing(self, tmp_path: Path) -> None:
        runner = CliRunner()
        mock_indexer = MagicMock()
        mock_indexer.index.return_value = {
            "files_indexed": 3,
            "chunks_created": 15,
            "files_skipped": 0,
        }

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = runner.invoke(main, ["index"])

        assert result.exit_code == 0
        assert "Files indexed:" in result.output


class TestProjectsCommand:
    """Tests for projects command."""

    def test_projects_list_empty(self) -> None:
        runner = CliRunner()
        with patch("personality.index.list_indexed_projects", return_value={}):
            result = runner.invoke(main, ["projects", "list"])
        assert result.exit_code == 0
        assert "No projects indexed" in result.output

    def test_projects_list_shows_projects(self) -> None:
        runner = CliRunner()
        registry = {"/path/to/project": "/tmp/abc123.db"}
        with patch("personality.index.list_indexed_projects", return_value=registry):
            result = runner.invoke(main, ["projects", "list"])
        assert result.exit_code == 0
        assert "project" in result.output


class TestHookCommands:
    """Tests for hook CLI commands."""

    def test_hook_session_start(self) -> None:
        runner = CliRunner()
        with patch("personality.hooks.session_start") as mock_start:
            mock_start.return_value = MagicMock(to_json=lambda: '{"status":"ok"}')
            result = runner.invoke(main, ["hook", "session-start"])
        assert result.exit_code == 0
        assert "ok" in result.output

    def test_hook_session_end(self) -> None:
        runner = CliRunner()
        with patch("personality.hooks.session_end") as mock_end:
            mock_end.return_value = MagicMock(to_json=lambda: '{"status":"ok"}')
            result = runner.invoke(main, ["hook", "session-end"])
        assert result.exit_code == 0

    def test_hook_stop(self) -> None:
        runner = CliRunner()
        with patch("personality.hooks.stop") as mock_stop:
            mock_stop.return_value = MagicMock(to_json=lambda: '{"status":"ok"}')
            result = runner.invoke(main, ["hook", "stop"])
        assert result.exit_code == 0

    def test_hook_notify_with_message(self) -> None:
        runner = CliRunner()
        with patch("personality.hooks.notify") as mock_notify:
            mock_notify.return_value = MagicMock(to_json=lambda: '{"status":"ok"}')
            result = runner.invoke(main, ["hook", "notify", "-m", "Hello"])
        assert result.exit_code == 0
        mock_notify.assert_called_once()
