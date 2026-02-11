"""Tests for personality.mcp.server module."""

import os
from unittest.mock import patch

import pytest

from personality.mcp.server import AppContext, _get_active_cart, create_server


class TestAppContext:
    """Tests for AppContext dataclass."""

    def test_stores_cart_name(self) -> None:
        ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/voices", memory=None)
        assert ctx.cart_name == "test"

    def test_stores_cart_data(self) -> None:
        data = {"preferences": {"identity": {"name": "Test"}}}
        ctx = AppContext(cart_name="test", cart_data=data, voice_dir="/voices", memory=None)
        assert ctx.cart_data == data

    def test_stores_voice_dir(self) -> None:
        ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/custom/voices", memory=None)
        assert ctx.voice_dir == "/custom/voices"

    def test_stores_memory(self) -> None:
        ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/voices", memory=None)
        assert ctx.memory is None


class TestGetActiveCart:
    """Tests for _get_active_cart function."""

    def test_returns_default_cart_when_env_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("personality.mcp.server.load_cart", return_value=None):
                name, data = _get_active_cart()
        assert name == "bt7274"

    def test_returns_cart_from_environment(self) -> None:
        with patch.dict(os.environ, {"PERSONALITY_CART": "custom"}):
            with patch("personality.mcp.server.load_cart", return_value={"test": True}):
                name, data = _get_active_cart()
        assert name == "custom"
        assert data == {"test": True}


class TestCreateServer:
    """Tests for create_server function."""

    def test_returns_fastmcp_instance(self) -> None:
        server = create_server()
        assert server is not None
        assert server.name == "personality"


@pytest.mark.asyncio
async def test_app_lifespan():
    """Test app_lifespan context manager."""
    from personality.mcp.server import app_lifespan, mcp

    with patch("personality.mcp.server.load_cart", return_value={"preferences": {}}):
        with patch.dict(os.environ, {"PERSONALITY_CART": "test"}):
            async with app_lifespan(mcp) as ctx:
                assert ctx.cart_name == "test"
                assert ctx.cart_data == {"preferences": {}}
                assert ctx.voice_dir is not None


class TestRunServer:
    """Tests for run_server function."""

    def test_imports_and_runs_mcp(self) -> None:
        from personality.mcp.server import run_server

        with patch("personality.mcp.server.mcp") as mock_mcp:
            run_server()
        mock_mcp.run.assert_called_once_with(transport="stdio")
