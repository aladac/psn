"""Tests for personality.config module."""

from personality.config import get_cart_identity, get_cart_voice


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
