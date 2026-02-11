"""Tests for personality.mcp.prompts module."""

from unittest.mock import MagicMock

import pytest

from personality.mcp.server import AppContext
from personality.mcp.prompts import _get_ctx, speak


class TestGetCtx:
    """Tests for _get_ctx helper function."""

    def test_extracts_app_context(self) -> None:
        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/voices", memory=None)
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = app_ctx
        result = _get_ctx(mock_ctx)
        assert result is app_ctx


class TestSpeakPrompt:
    """Tests for speak prompt."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock MCP context with cart data."""
        app_ctx = AppContext(
            cart_name="test",
            cart_data={
                "preferences": {
                    "identity": {"name": "Test Bot"},
                    "speak": {"voice": "test_voice"},
                }
            },
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
    async def test_generates_speak_prompt_with_persona(
        self, mock_context: MagicMock
    ) -> None:
        result = await speak("Hello world", mock_context)
        assert "Test Bot" in result
        assert "voice: test_voice" in result
        assert "Hello world" in result
        assert "speak" in result.lower()

    @pytest.mark.asyncio
    async def test_uses_cart_name_when_no_identity(
        self, mock_context_no_cart: MagicMock
    ) -> None:
        result = await speak("Hello", mock_context_no_cart)
        assert "fallback" in result
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_omits_voice_when_not_configured(
        self, mock_context_no_cart: MagicMock
    ) -> None:
        result = await speak("Hello", mock_context_no_cart)
        assert "voice:" not in result

    @pytest.mark.asyncio
    async def test_includes_tool_instruction(self, mock_context: MagicMock) -> None:
        result = await speak("Test", mock_context)
        assert "speak" in result.lower()
        assert "tool" in result.lower()
