"""Tests for personality.mcp.tools module."""

from unittest.mock import MagicMock, patch

import pytest

from personality.mcp.server import AppContext
from personality.mcp.tools import _get_ctx, speak


class TestGetCtx:
    """Tests for _get_ctx helper function."""

    def test_extracts_app_context(self) -> None:
        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/voices", memory=None)
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = app_ctx
        result = _get_ctx(mock_ctx)
        assert result is app_ctx


class TestSpeakTool:
    """Tests for speak tool."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock MCP context."""
        app_ctx = AppContext(
            cart_name="test",
            cart_data={"preferences": {"speak": {"voice": "cart_voice"}}},
            voice_dir="/tmp/voices",
            memory=None,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.fixture
    def mock_context_no_cart(self) -> MagicMock:
        """Create a mock MCP context with no cart data."""
        app_ctx = AppContext(cart_name="fallback", cart_data=None, voice_dir="/tmp/voices", memory=None)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_returns_error_for_empty_text(self, mock_context: MagicMock) -> None:
        result = await speak("", mock_context)
        assert "Error: No text provided" in result

    @pytest.mark.asyncio
    async def test_returns_error_for_whitespace_text(self, mock_context: MagicMock) -> None:
        result = await speak("   ", mock_context)
        assert "Error: No text provided" in result

    @pytest.mark.asyncio
    async def test_uses_voice_override(self, mock_context: MagicMock) -> None:
        mock_speaker = MagicMock()
        with patch("personality.mcp.tools.Speak", return_value=mock_speaker):
            result = await speak("hello", mock_context, voice="override_voice")
        mock_speaker.say.assert_called_once_with("hello", "override_voice")
        assert "Spoke:" in result

    @pytest.mark.asyncio
    async def test_uses_cart_voice_when_no_override(self, mock_context: MagicMock) -> None:
        mock_speaker = MagicMock()
        with patch("personality.mcp.tools.Speak", return_value=mock_speaker):
            await speak("hello", mock_context)
        mock_speaker.say.assert_called_once_with("hello", "cart_voice")

    @pytest.mark.asyncio
    async def test_uses_cart_name_as_fallback(self, mock_context_no_cart: MagicMock) -> None:
        mock_speaker = MagicMock()
        with patch("personality.mcp.tools.Speak", return_value=mock_speaker):
            await speak("hello", mock_context_no_cart)
        mock_speaker.say.assert_called_once_with("hello", "fallback")

    @pytest.mark.asyncio
    async def test_handles_voice_not_found(self, mock_context: MagicMock) -> None:
        mock_speaker = MagicMock()
        mock_speaker.say.side_effect = FileNotFoundError("Voice not found")
        with (
            patch("personality.mcp.tools.Speak", return_value=mock_speaker),
            patch("personality.mcp.tools.logger"),
        ):
            result = await speak("hello", mock_context)
        assert "Voice not found:" in result

    @pytest.mark.asyncio
    async def test_handles_playback_error(self, mock_context: MagicMock) -> None:
        mock_speaker = MagicMock()
        mock_speaker.say.side_effect = RuntimeError("No player")
        with (
            patch("personality.mcp.tools.Speak", return_value=mock_speaker),
            patch("personality.mcp.tools.logger"),
        ):
            result = await speak("hello", mock_context)
        assert "Playback error:" in result

    @pytest.mark.asyncio
    async def test_handles_generic_error(self, mock_context: MagicMock) -> None:
        mock_speaker = MagicMock()
        mock_speaker.say.side_effect = ValueError("Something went wrong")
        with (
            patch("personality.mcp.tools.Speak", return_value=mock_speaker),
            patch("personality.mcp.tools.logger"),
        ):
            result = await speak("hello", mock_context)
        assert "Error:" in result

    @pytest.mark.asyncio
    async def test_truncates_long_text_in_response(self, mock_context: MagicMock) -> None:
        mock_speaker = MagicMock()
        long_text = "a" * 100
        with patch("personality.mcp.tools.Speak", return_value=mock_speaker):
            result = await speak(long_text, mock_context)
        assert "..." in result
        assert len(result) < len(long_text) + 20


class TestCartExportTool:
    """Tests for cart_export MCP tool."""

    @pytest.mark.asyncio
    async def test_exports_cart_successfully(self, tmp_path) -> None:
        from personality.mcp.tools import cart_export

        mock_pcart = MagicMock()
        mock_pcart.manifest.components = {"core": True}

        with patch("personality.cart.PortableCart.export", return_value=mock_pcart):
            result = await cart_export("test", str(tmp_path / "out"))

        assert "Exported" in result
        assert "test" in result

    @pytest.mark.asyncio
    async def test_handles_export_error(self) -> None:
        from personality.mcp.tools import cart_export

        with (
            patch("personality.cart.PortableCart.export", side_effect=ValueError("Not found")),
            patch("personality.mcp.tools.logger"),
        ):
            result = await cart_export("missing", "/tmp/out")

        assert "Error" in result


class TestCartImportTool:
    """Tests for cart_import MCP tool."""

    @pytest.mark.asyncio
    async def test_imports_cart_successfully(self, tmp_path) -> None:
        from personality.mcp.tools import cart_import

        pcart_dir = tmp_path / "test.pcart"
        pcart_dir.mkdir()

        mock_pcart = MagicMock()
        mock_pcart.install.return_value = {"cart_name": "test", "actions": ["Installed"]}

        with patch("personality.cart.PortableCart.load", return_value=mock_pcart):
            result = await cart_import(str(pcart_dir))

        assert "Installed" in result
        assert "test" in result

    @pytest.mark.asyncio
    async def test_handles_missing_path(self) -> None:
        from personality.mcp.tools import cart_import

        result = await cart_import("/nonexistent/path")

        assert "not found" in result

    @pytest.mark.asyncio
    async def test_handles_import_error(self, tmp_path) -> None:
        from personality.mcp.tools import cart_import

        pcart_dir = tmp_path / "test.pcart"
        pcart_dir.mkdir()

        with (
            patch("personality.cart.PortableCart.load", side_effect=ValueError("Bad format")),
            patch("personality.mcp.tools.logger"),
        ):
            result = await cart_import(str(pcart_dir))

        assert "Error" in result
