"""
Cart manager service.

Manages saving and loading persona data as cartridge (`.pcart`) files.
A .pcart file is a ZIP archive containing persona.yml and preferences.yml.
"""

import zipfile
from datetime import datetime
from pathlib import Path

import yaml

from personality.schemas.pcart import (
    CartManifest,
    Cartridge,
    PersonaConfig,
    PreferencesConfig,
)
from personality.schemas.training import TrainingMemory
from personality.services.training_parser import TrainingParser

# Cart file extension
CART_EXTENSION = ".pcart"

# Cart schema version
CART_SCHEMA_VERSION = 1


class CartManager:
    """
    Service for managing cartridge files.

    Cartridges are ZIP archives containing persona memories and preferences
    in a portable format.
    """

    def __init__(self, carts_dir: Path | None = None) -> None:
        """
        Initialize the cart manager.

        Args:
            carts_dir: Directory for storing carts. Defaults to plugin carts/.
        """
        if carts_dir is None:
            carts_dir = Path(__file__).parent.parent.parent.parent / "carts"
        self._carts_dir = carts_dir

    @property
    def carts_dir(self) -> Path:
        """Get the carts directory."""
        return self._carts_dir

    def load_cart(self, path: Path) -> Cartridge:
        """
        Load a cartridge from a .pcart file.

        Args:
            path: Path to the .pcart file.

        Returns:
            Loaded Cartridge.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If file is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Cart file not found: {path}")

        try:
            with zipfile.ZipFile(path, "r") as zf:
                # Read persona.yml (required)
                if "persona.yml" not in zf.namelist():
                    raise ValueError("Missing persona.yml in cart")

                persona_yaml = zf.read("persona.yml").decode("utf-8")
                persona_data = yaml.safe_load(persona_yaml) or {}

                # Parse persona config
                tag = persona_data.get("tag", path.stem)
                version = str(persona_data.get("version", ""))

                # Parse memories
                memories: list[TrainingMemory] = []
                for item in persona_data.get("memories", []):
                    if isinstance(item, dict) and "subject" in item and "content" in item:
                        content = item["content"]
                        if isinstance(content, list):
                            content = ", ".join(str(x) for x in content)
                        memories.append(
                            TrainingMemory(
                                subject=str(item["subject"]),
                                content=str(content),
                            )
                        )

                persona = PersonaConfig(
                    tag=tag,
                    version=version,
                    memories=memories,
                )

                # Read preferences.yml (optional)
                preferences_data: dict = {}
                if "preferences.yml" in zf.namelist():
                    prefs_yaml = zf.read("preferences.yml").decode("utf-8")
                    preferences_data = yaml.safe_load(prefs_yaml) or {}

                # Also check for preferences in persona.yml (training format)
                if "preferences" in persona_data:
                    # Merge, preferences.yml takes precedence
                    base_prefs = persona_data["preferences"]
                    for key, value in base_prefs.items():
                        if key not in preferences_data:
                            preferences_data[key] = value

                preferences = PreferencesConfig.from_dict(preferences_data)

                # Create manifest
                manifest = CartManifest(
                    schema_version=CART_SCHEMA_VERSION,
                    tag=tag,
                    version=version,
                    memory_count=len(memories),
                )

                return Cartridge(
                    path=path,
                    manifest=manifest,
                    persona=persona,
                    preferences=preferences,
                )

        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid cart file: {e}") from e

    def save_cart(self, cart: Cartridge, path: Path | None = None) -> Path:
        """
        Save a cartridge to a .pcart file.

        Args:
            cart: The cartridge to save.
            path: Output path. Defaults to carts_dir/tag.pcart.

        Returns:
            Path to the saved file.
        """
        if path is None:
            self._carts_dir.mkdir(parents=True, exist_ok=True)
            path = self._carts_dir / f"{cart.tag}{CART_EXTENSION}"

        # Serialize persona.yml
        persona_dict = {
            "tag": cart.persona.tag,
            "version": cart.persona.version,
            "memories": [{"subject": m.subject, "content": m.content} for m in cart.persona.memories],
        }
        persona_yaml = yaml.dump(persona_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Serialize preferences.yml
        prefs_dict = cart.preferences.to_dict()
        prefs_yaml = yaml.dump(prefs_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Write ZIP archive
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("persona.yml", persona_yaml)
            zf.writestr("preferences.yml", prefs_yaml)

        return path

    def create_from_training(self, training_path: Path, output_path: Path | None = None) -> Cartridge:
        """
        Create a cartridge from a training YAML file.

        Args:
            training_path: Path to the training file.
            output_path: Output path for the .pcart file.

        Returns:
            The created Cartridge.
        """
        parser = TrainingParser()
        doc = parser.parse_file(training_path)

        # Create persona config
        persona = PersonaConfig(
            tag=doc.tag or training_path.stem.lower(),
            version=doc.version,
            memories=doc.memories,
        )

        # Create preferences from training
        preferences = PreferencesConfig.from_dict(doc.preferences)

        # Create manifest
        manifest = CartManifest(
            schema_version=CART_SCHEMA_VERSION,
            tag=persona.tag,
            version=persona.version,
            created_at=datetime.now(),
            memory_count=len(doc.memories),
        )

        cart = Cartridge(
            path=None,
            manifest=manifest,
            persona=persona,
            preferences=preferences,
        )

        # Determine output path
        if output_path is None:
            self._carts_dir.mkdir(parents=True, exist_ok=True)
            output_path = self._carts_dir / f"{persona.tag}{CART_EXTENSION}"

        # Save and update path
        saved_path = self.save_cart(cart, output_path)
        cart.path = saved_path

        return cart

    def list_carts(self) -> list[Path]:
        """
        List available cartridge files.

        Returns:
            List of cart file paths.
        """
        if not self._carts_dir.exists():
            return []

        return sorted(self._carts_dir.glob(f"*{CART_EXTENSION}"))

    def get_cart_info(self, path: Path) -> dict:
        """
        Get basic info about a cart without fully loading it.

        Args:
            path: Path to the cart file.

        Returns:
            Dict with tag, version, memory_count.
        """
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if "persona.yml" not in zf.namelist():
                    return {"error": "Missing persona.yml"}

                persona_yaml = zf.read("persona.yml").decode("utf-8")
                data = yaml.safe_load(persona_yaml) or {}

                return {
                    "tag": data.get("tag", path.stem),
                    "version": str(data.get("version", "")),
                    "memory_count": len(data.get("memories", [])),
                }
        except Exception as e:
            return {"error": str(e)}

    def validate_cart(self, path: Path) -> tuple[bool, str]:
        """
        Validate a cartridge file.

        Args:
            path: Path to the cart file.

        Returns:
            Tuple of (is_valid, message).
        """
        if not path.exists():
            return False, f"File not found: {path}"

        try:
            cart = self.load_cart(path)
            return True, f"Valid: {cart.tag} v{cart.manifest.version}, {cart.memory_count} memories"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"
