"""
Cart registry service.

Tracks available and active cartridges.
"""

from pathlib import Path
from typing import Any

import yaml

from personality.schemas.pcart import Cartridge
from personality.services.cart_manager import CART_EXTENSION, CartManager

# State file name
STATE_FILE = "current_cart.yml"


class CartRegistry:
    """
    Registry for tracking available and active cartridges.

    Maintains state in a YAML file to persist the active cart across sessions.
    """

    def __init__(
        self,
        carts_dir: Path | None = None,
        state_dir: Path | None = None,
    ) -> None:
        """
        Initialize the cart registry.

        Args:
            carts_dir: Directory containing .pcart files.
            state_dir: Directory for state file. Defaults to carts_dir.
        """
        if carts_dir is None:
            carts_dir = Path(__file__).parent.parent.parent.parent / "carts"
        if state_dir is None:
            state_dir = carts_dir

        self._carts_dir = carts_dir
        self._state_dir = state_dir
        self._manager = CartManager(carts_dir)
        self._active_cart: Cartridge | None = None

    @property
    def carts_dir(self) -> Path:
        """Get the carts directory."""
        return self._carts_dir

    @property
    def state_file(self) -> Path:
        """Get the state file path."""
        return self._state_dir / STATE_FILE

    def list_available(self) -> list[dict[str, Any]]:
        """
        List all available cartridges with basic info.

        Returns:
            List of cart info dicts.
        """
        carts = []
        for path in self._manager.list_carts():
            info = self._manager.get_cart_info(path)
            info["path"] = str(path)
            info["filename"] = path.name
            carts.append(info)
        return carts

    def get_active(self) -> Cartridge | None:
        """
        Get the currently active cartridge.

        Returns:
            Active Cartridge or None.
        """
        if self._active_cart is not None:
            return self._active_cart

        # Try to load from state file
        state = self._load_state()
        if state and "active" in state:
            active_tag = state["active"]
            try:
                self._active_cart = self.load_by_tag(active_tag)
                return self._active_cart
            except (FileNotFoundError, ValueError):
                pass

        return None

    def get_active_tag(self) -> str | None:
        """
        Get the tag of the active cartridge.

        Returns:
            Active cart tag or None.
        """
        cart = self.get_active()
        return cart.tag if cart else None

    def load_by_tag(self, tag: str) -> Cartridge:
        """
        Load a cartridge by its tag.

        Args:
            tag: The persona tag.

        Returns:
            Loaded Cartridge.

        Raises:
            FileNotFoundError: If cart not found.
        """
        # Try exact match first
        path = self._carts_dir / f"{tag}{CART_EXTENSION}"
        if path.exists():
            return self._manager.load_cart(path)

        # Try case-insensitive match
        tag_lower = tag.lower()
        for cart_path in self._manager.list_carts():
            if cart_path.stem.lower() == tag_lower:
                return self._manager.load_cart(cart_path)

        raise FileNotFoundError(f"Cart not found: {tag}")

    def switch_to(self, tag: str) -> Cartridge:
        """
        Switch to a different cartridge.

        Args:
            tag: The persona tag to switch to.

        Returns:
            The newly active Cartridge.

        Raises:
            FileNotFoundError: If cart not found.
        """
        cart = self.load_by_tag(tag)
        self._active_cart = cart
        self._save_state({"active": cart.tag})
        return cart

    def clear_active(self) -> None:
        """Clear the active cartridge."""
        self._active_cart = None
        self._save_state({})

    def create_from_training(self, training_path: Path) -> Cartridge:
        """
        Create a new cartridge from a training file.

        Args:
            training_path: Path to the training YAML file.

        Returns:
            The created Cartridge.
        """
        return self._manager.create_from_training(training_path)

    def _load_state(self) -> dict[str, Any]:
        """Load state from file."""
        if not self.state_file.exists():
            return {}

        try:
            content = self.state_file.read_text(encoding="utf-8")
            return yaml.safe_load(content) or {}
        except Exception:
            return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        """Save state to file."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        content = yaml.dump(state, default_flow_style=False)
        self.state_file.write_text(content, encoding="utf-8")
