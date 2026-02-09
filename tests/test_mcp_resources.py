"""Tests for personality.mcp.resources module."""

import os
from unittest.mock import patch

from personality.mcp.resources import (
    _format_cart,
    get_cart_by_name,
    get_current_cart,
    list_available_carts,
)


class TestFormatCart:
    """Tests for _format_cart helper function."""

    def test_returns_not_found_for_missing_cart(self) -> None:
        with patch("personality.mcp.resources.load_cart", return_value=None):
            result = _format_cart("missing")
        assert "Cart not found: missing" in result

    def test_formats_cart_with_identity(self) -> None:
        cart_data = {
            "preferences": {
                "identity": {"name": "Test Bot", "tagline": "Hello world"},
                "speak": {"voice": "test"},
            }
        }
        with patch("personality.mcp.resources.load_cart", return_value=cart_data):
            result = _format_cart("test")
        assert "# Test Bot" in result
        assert "tagline" in result
        assert "Hello world" in result

    def test_formats_cart_with_voice(self) -> None:
        cart_data = {"preferences": {"speak": {"voice": "custom_voice"}}}
        with patch("personality.mcp.resources.load_cart", return_value=cart_data):
            result = _format_cart("test")
        assert "custom_voice" in result

    def test_formats_cart_with_memories(self) -> None:
        cart_data = {
            "preferences": {},
            "memories": [
                {"subject": "protocol1", "content": "Protect the pilot"},
                {"subject": "protocol2", "content": ["item1", "item2"]},
            ],
        }
        with patch("personality.mcp.resources.load_cart", return_value=cart_data):
            result = _format_cart("test")
        assert "Memories" in result
        assert "protocol1" in result
        assert "Protect the pilot" in result
        assert "item1, item2" in result

    def test_limits_memories_to_ten(self) -> None:
        memories = [{"subject": f"mem{i}", "content": f"content{i}"} for i in range(15)]
        cart_data = {"preferences": {}, "memories": memories}
        with patch("personality.mcp.resources.load_cart", return_value=cart_data):
            result = _format_cart("test")
        assert "5 more memories" in result


class TestGetCurrentCart:
    """Tests for get_current_cart resource."""

    def test_uses_default_cart_when_env_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("personality.mcp.resources.load_cart", return_value=None):
                result = get_current_cart()
        assert "bt7274" in result

    def test_uses_cart_from_environment(self) -> None:
        cart_data = {"preferences": {"identity": {"name": "Custom"}}}
        with patch.dict(os.environ, {"PERSONALITY_CART": "custom"}):
            with patch("personality.mcp.resources.load_cart", return_value=cart_data):
                result = get_current_cart()
        assert "Custom" in result


class TestGetCartByName:
    """Tests for get_cart_by_name resource."""

    def test_returns_formatted_cart(self) -> None:
        cart_data = {"preferences": {"identity": {"name": "Named Cart"}}}
        with patch("personality.mcp.resources.load_cart", return_value=cart_data):
            result = get_cart_by_name("named")
        assert "Named Cart" in result

    def test_returns_not_found_for_missing(self) -> None:
        with patch("personality.mcp.resources.load_cart", return_value=None):
            result = get_cart_by_name("missing")
        assert "Cart not found" in result


class TestListAvailableCarts:
    """Tests for list_available_carts resource."""

    def test_returns_no_carts_message(self) -> None:
        with patch("personality.mcp.resources.list_carts", return_value=[]):
            result = list_available_carts()
        assert "No carts found" in result

    def test_lists_carts_with_details(self) -> None:
        cart_data = {
            "preferences": {"identity": {"name": "Test"}, "speak": {"voice": "v1"}}
        }
        with patch("personality.mcp.resources.list_carts", return_value=["test", "other"]):
            with patch("personality.mcp.resources.load_cart", return_value=cart_data):
                result = list_available_carts()
        assert "Available Carts" in result
        assert "test" in result

    def test_handles_failed_cart_load(self) -> None:
        def load_side_effect(name: str) -> dict | None:
            return None if name == "broken" else {"preferences": {}}

        with patch("personality.mcp.resources.list_carts", return_value=["good", "broken"]):
            with patch("personality.mcp.resources.load_cart", side_effect=load_side_effect):
                result = list_available_carts()
        assert "failed to load" in result
