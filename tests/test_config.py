"""Tests for personality.config module."""

from pathlib import Path
from unittest.mock import patch

from personality.config import (
    get_cart_identity,
    get_cart_voice,
    get_carts_dir,
    get_voices_dir,
    list_carts,
    load_cart,
)


class TestGetCartVoice:
    """Tests for get_cart_voice function."""

    def test_returns_voice_from_speak_key(self) -> None:
        cart = {"preferences": {"speak": {"voice": "test-voice"}}}
        assert get_cart_voice(cart) == "test-voice"

    def test_returns_voice_from_legacy_tts_key(self) -> None:
        cart = {"preferences": {"tts": {"voice": "legacy-voice"}}}
        assert get_cart_voice(cart) == "legacy-voice"

    def test_speak_takes_precedence_over_tts(self) -> None:
        cart = {
            "preferences": {
                "speak": {"voice": "speak-voice"},
                "tts": {"voice": "tts-voice"},
            }
        }
        assert get_cart_voice(cart) == "speak-voice"

    def test_returns_none_when_no_voice(self) -> None:
        cart = {"preferences": {}}
        assert get_cart_voice(cart) is None

    def test_returns_none_for_empty_cart(self) -> None:
        assert get_cart_voice({}) is None


class TestGetCartIdentity:
    """Tests for get_cart_identity function."""

    def test_returns_identity_dict(self) -> None:
        cart = {"preferences": {"identity": {"name": "Test", "tagline": "Hello"}}}
        identity = get_cart_identity(cart)
        assert identity == {"name": "Test", "tagline": "Hello"}

    def test_returns_empty_dict_when_no_identity(self) -> None:
        cart = {"preferences": {}}
        assert get_cart_identity(cart) == {}

    def test_returns_empty_dict_for_empty_cart(self) -> None:
        assert get_cart_identity({}) == {}


class TestGetCartsDir:
    """Tests for get_carts_dir function."""

    def test_returns_path(self) -> None:
        result = get_carts_dir()
        assert isinstance(result, Path)
        assert "carts" in str(result)


class TestGetVoicesDir:
    """Tests for get_voices_dir function."""

    def test_returns_path(self) -> None:
        result = get_voices_dir()
        assert isinstance(result, Path)
        assert "voices" in str(result)


class TestListCarts:
    """Tests for list_carts function."""

    def test_returns_empty_list_when_dir_not_exists(self, tmp_path: Path) -> None:
        with patch("personality.config.CARTS_DIR", tmp_path / "missing"):
            result = list_carts()
        assert result == []

    def test_returns_cart_names(self, tmp_path: Path) -> None:
        (tmp_path / "cart1.yml").touch()
        (tmp_path / "cart2.yml").touch()
        (tmp_path / "notacart.txt").touch()
        with patch("personality.config.CARTS_DIR", tmp_path):
            result = list_carts()
        assert sorted(result) == ["cart1", "cart2"]


class TestLoadCart:
    """Tests for load_cart function."""

    def test_returns_none_when_cart_not_found(self, tmp_path: Path) -> None:
        with patch("personality.config.CARTS_DIR", tmp_path):
            result = load_cart("missing")
        assert result is None

    def test_loads_cart_yaml(self, tmp_path: Path) -> None:
        cart_file = tmp_path / "test.yml"
        cart_file.write_text("preferences:\n  identity:\n    name: Test\n")
        with patch("personality.config.CARTS_DIR", tmp_path):
            result = load_cart("test")
        assert result == {"preferences": {"identity": {"name": "Test"}}}
