"""Portable cartridge format (.pcart) for export/import."""

import hashlib
import json
import logging
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml

from personality.config import CARTS_DIR, CONFIG_DIR, VOICES_DIR, load_cart

logger = logging.getLogger(__name__)

MANIFEST_VERSION = "1.0"
MEMORY_DIR = CONFIG_DIR / "memory"


class InstallMode(str, Enum):
    """Installation modes for importing carts."""

    SAFE = "safe"  # Fail if cart exists
    OVERRIDE = "override"  # Replace existing
    MERGE = "merge"  # Merge memories and preferences
    DRY_RUN = "dry_run"  # Preview only


@dataclass
class Manifest:
    """Portable cart manifest."""

    version: str = MANIFEST_VERSION
    cart_name: str = ""
    created_at: str = ""
    checksums: dict = field(default_factory=dict)
    components: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "cart_name": self.cart_name,
            "created_at": self.created_at,
            "checksums": self.checksums,
            "components": self.components,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        """Create from dictionary."""
        return cls(
            version=data.get("version", MANIFEST_VERSION),
            cart_name=data.get("cart_name", ""),
            created_at=data.get("created_at", ""),
            checksums=data.get("checksums", {}),
            components=data.get("components", {}),
        )


def _compute_checksum(path: Path) -> str:
    """Compute MD5 checksum of a file."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def _extract_core(cart_data: dict) -> dict:
    """Extract immutable core from cart data."""
    prefs = cart_data.get("preferences", {})
    return {
        "identity": prefs.get("identity", {}),
        "traits": prefs.get("traits", []),
        "protocols": prefs.get("protocols", []),
        "communication_style": prefs.get("communication_style", {}),
    }


def _extract_preferences(cart_data: dict) -> dict:
    """Extract mutable preferences from cart data."""
    prefs = cart_data.get("preferences", {})
    return {
        "speak": prefs.get("speak", {}),
        "overrides": prefs.get("overrides", {}),
        "stats": prefs.get("stats", {}),
    }


class PortableCart:
    """Handle portable cart export and import."""

    def __init__(self, path: Path):
        """Initialize with a .pcart directory or ZIP path."""
        self.path = path
        self._manifest: Manifest | None = None
        self._temp_dir: Path | None = None

    @property
    def manifest(self) -> Manifest:
        """Load and return manifest."""
        if self._manifest is None:
            manifest_path = self._get_content_path() / "manifest.json"
            if manifest_path.exists():
                self._manifest = Manifest.from_dict(json.loads(manifest_path.read_text()))
            else:
                self._manifest = Manifest()
        return self._manifest

    def _get_content_path(self) -> Path:
        """Get path to content (extract ZIP if needed)."""
        if self.path.suffix == ".zip":
            if self._temp_dir is None:
                self._temp_dir = Path(tempfile.mkdtemp())
                with zipfile.ZipFile(self.path, "r") as zf:
                    zf.extractall(self._temp_dir)
            return self._temp_dir
        return self.path

    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
            self._temp_dir = None

    @classmethod
    def export(
        cls,
        cart_name: str,
        output_path: Path,
        include_voice: bool = True,
        include_memories: bool = True,
        as_zip: bool = False,
    ) -> "PortableCart":
        """Export a cart to portable format."""
        cart_data = load_cart(cart_name)
        if not cart_data:
            raise ValueError(f"Cart not found: {cart_name}")

        # Create output directory
        if as_zip:
            temp_dir = Path(tempfile.mkdtemp())
            content_path = temp_dir
        else:
            content_path = output_path
            content_path.mkdir(parents=True, exist_ok=True)

        manifest = Manifest(
            cart_name=cart_name,
            created_at=datetime.now().isoformat(),
            components={"core": True, "preferences": True},
        )

        # Write core.yml
        core_data = _extract_core(cart_data)
        core_path = content_path / "core.yml"
        core_path.write_text(yaml.dump(core_data, default_flow_style=False))
        manifest.checksums["core.yml"] = _compute_checksum(core_path)

        # Write preferences.yml
        prefs_data = _extract_preferences(cart_data)
        prefs_path = content_path / "preferences.yml"
        prefs_path.write_text(yaml.dump(prefs_data, default_flow_style=False))
        manifest.checksums["preferences.yml"] = _compute_checksum(prefs_path)

        # Copy memories if present and requested
        memory_db = MEMORY_DIR / f"{cart_name}.db"
        if include_memories and memory_db.exists():
            dest_memory = content_path / "memory.db"
            shutil.copy2(memory_db, dest_memory)
            manifest.checksums["memory.db"] = _compute_checksum(dest_memory)
            manifest.components["memories"] = True

        # Copy voice if present and requested
        if include_voice:
            voice_name = cart_data.get("preferences", {}).get("speak", {}).get("voice")
            if voice_name:
                voice_path = VOICES_DIR / f"{voice_name}.onnx"
                if voice_path.exists():
                    dest_voice = content_path / f"{voice_name}.onnx"
                    shutil.copy2(voice_path, dest_voice)
                    manifest.checksums[f"{voice_name}.onnx"] = _compute_checksum(dest_voice)
                    manifest.components["voice"] = voice_name

                    # Copy voice config if exists
                    voice_config = VOICES_DIR / f"{voice_name}.onnx.json"
                    if voice_config.exists():
                        dest_config = content_path / f"{voice_name}.onnx.json"
                        shutil.copy2(voice_config, dest_config)
                        manifest.checksums[f"{voice_name}.onnx.json"] = _compute_checksum(dest_config)

        # Write manifest
        manifest_path = content_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))

        # Create ZIP if requested
        if as_zip:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in content_path.rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, file_path.relative_to(content_path))
            shutil.rmtree(temp_dir)

        logger.info("Exported cart %s to %s", cart_name, output_path)
        return cls(output_path)

    @classmethod
    def load(cls, path: Path) -> "PortableCart":
        """Load a portable cart from directory or ZIP."""
        if not path.exists():
            raise FileNotFoundError(f"Cart not found: {path}")
        return cls(path)

    def verify(self) -> dict:
        """Verify checksums of all components."""
        content_path = self._get_content_path()
        results = {}

        for filename, expected_hash in self.manifest.checksums.items():
            file_path = content_path / filename
            if not file_path.exists():
                results[filename] = "missing"
            else:
                actual_hash = _compute_checksum(file_path)
                results[filename] = "valid" if actual_hash == expected_hash else "corrupted"

        return results

    def install(self, mode: InstallMode = InstallMode.SAFE, target_name: str | None = None) -> dict:
        """Install the portable cart."""
        cart_name = target_name or self.manifest.cart_name
        content_path = self._get_content_path()
        stats = {"cart_name": cart_name, "mode": mode.value, "actions": []}

        # Check if cart exists
        existing_cart = CARTS_DIR / f"{cart_name}.yml"
        if existing_cart.exists():
            if mode == InstallMode.SAFE:
                raise ValueError(f"Cart already exists: {cart_name}. Use --mode override or merge")
            if mode == InstallMode.DRY_RUN:
                stats["actions"].append(f"Would replace existing cart: {cart_name}")

        if mode == InstallMode.DRY_RUN:
            stats["actions"].append("Dry run - no changes made")
            return stats

        CARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Build cart from core and preferences
        core_path = content_path / "core.yml"
        prefs_path = content_path / "preferences.yml"

        cart_data = {"preferences": {}}
        if core_path.exists():
            core = yaml.safe_load(core_path.read_text()) or {}
            cart_data["preferences"].update(core)
        if prefs_path.exists():
            prefs = yaml.safe_load(prefs_path.read_text()) or {}
            cart_data["preferences"].update(prefs)

        # Handle merge mode for existing cart
        if mode == InstallMode.MERGE and existing_cart.exists():
            existing_data = yaml.safe_load(existing_cart.read_text()) or {}
            cart_data = self._merge_cart_data(existing_data, cart_data)
            stats["actions"].append("Merged with existing cart")

        # Write cart file
        cart_path = CARTS_DIR / f"{cart_name}.yml"
        cart_path.write_text(yaml.dump(cart_data, default_flow_style=False))
        stats["actions"].append(f"Installed cart: {cart_name}")

        # Handle memories
        memory_src = content_path / "memory.db"
        if memory_src.exists():
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            memory_dest = MEMORY_DIR / f"{cart_name}.db"

            if mode == InstallMode.MERGE and memory_dest.exists():
                self._merge_memories(memory_src, memory_dest)
                stats["actions"].append("Merged memories")
            else:
                shutil.copy2(memory_src, memory_dest)
                stats["actions"].append("Copied memories")

        # Handle voice
        voice_name = self.manifest.components.get("voice")
        if voice_name:
            VOICES_DIR.mkdir(parents=True, exist_ok=True)
            voice_src = content_path / f"{voice_name}.onnx"
            if voice_src.exists():
                voice_dest = VOICES_DIR / f"{voice_name}.onnx"
                if not voice_dest.exists() or mode == InstallMode.OVERRIDE:
                    shutil.copy2(voice_src, voice_dest)
                    stats["actions"].append(f"Installed voice: {voice_name}")

                    # Copy voice config
                    config_src = content_path / f"{voice_name}.onnx.json"
                    if config_src.exists():
                        config_dest = VOICES_DIR / f"{voice_name}.onnx.json"
                        shutil.copy2(config_src, config_dest)

        logger.info("Installed cart %s with mode %s", cart_name, mode.value)
        return stats

    def _merge_cart_data(self, existing: dict, new: dict) -> dict:
        """Merge cart data preserving user customizations."""
        result = {"preferences": {}}

        existing_prefs = existing.get("preferences", {})
        new_prefs = new.get("preferences", {})

        # Core identity comes from new
        for key in ["identity", "traits", "protocols", "communication_style"]:
            if key in new_prefs:
                result["preferences"][key] = new_prefs[key]
            elif key in existing_prefs:
                result["preferences"][key] = existing_prefs[key]

        # User preferences preserved from existing
        for key in ["speak", "overrides", "stats"]:
            if key in existing_prefs:
                result["preferences"][key] = existing_prefs[key]
            elif key in new_prefs:
                result["preferences"][key] = new_prefs[key]

        return result

    def _merge_memories(self, src: Path, dest: Path) -> None:
        """Merge memories from source into destination, deduplicating by content hash."""
        import sqlite3

        src_conn = sqlite3.connect(str(src))
        dest_conn = sqlite3.connect(str(dest))

        try:
            # Get existing content hashes
            existing_hashes = set()
            try:
                rows = dest_conn.execute("SELECT content FROM memories").fetchall()
                for row in rows:
                    existing_hashes.add(hashlib.md5(row[0].encode()).hexdigest())
            except sqlite3.OperationalError:
                pass  # Table might not exist

            # Insert new memories
            try:
                rows = src_conn.execute("SELECT subject, content, source, created_at FROM memories").fetchall()
                for subject, content, source, created_at in rows:
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    if content_hash not in existing_hashes:
                        dest_conn.execute(
                            "INSERT INTO memories (subject, content, source, created_at) VALUES (?, ?, ?, ?)",
                            (subject, content, source or "import", created_at),
                        )
                dest_conn.commit()
            except sqlite3.OperationalError as e:
                logger.warning("Could not merge memories: %s", e)
        finally:
            src_conn.close()
            dest_conn.close()
