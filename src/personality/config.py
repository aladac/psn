"""Configuration management for personality carts."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "personality"
CARTS_DIR = CONFIG_DIR / "carts"
VOICES_DIR = CONFIG_DIR / "voices"

# Default voice directory (uses config dir)
DEFAULT_VOICE_DIR = VOICES_DIR


def get_carts_dir() -> Path:
    """Get the carts directory path."""
    return CARTS_DIR


def get_voices_dir() -> Path:
    """Get the voices directory path."""
    return VOICES_DIR


def list_carts() -> list[str]:
    """List available cart names."""
    if not CARTS_DIR.exists():
        return []
    return [f.stem for f in CARTS_DIR.glob("*.yml")]


def load_cart(name: str) -> dict | None:
    """Load a cart by name.

    Args:
        name: Cart name (without .yml extension).

    Returns:
        Cart data as dict, or None if not found.
    """
    cart_path = CARTS_DIR / f"{name}.yml"
    if not cart_path.exists():
        logger.warning("Cart not found: %s", name)
        return None

    with cart_path.open() as f:
        return yaml.safe_load(f)


def get_cart_voice(cart: dict) -> str | None:
    """Extract voice name from cart preferences.

    Checks both 'speak' and legacy 'tts' preference keys.

    Args:
        cart: Loaded cart data.

    Returns:
        Voice name if configured, None otherwise.
    """
    prefs = cart.get("preferences", {})
    # Check 'speak' first, fall back to legacy 'tts'
    speak = prefs.get("speak", {}) or prefs.get("tts", {})
    return speak.get("voice")


def get_cart_identity(cart: dict) -> dict:
    """Extract identity info from cart preferences.

    Args:
        cart: Loaded cart data.

    Returns:
        Identity dict with name, tagline, etc.
    """
    prefs = cart.get("preferences", {})
    return prefs.get("identity", {})
