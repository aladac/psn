"""Tests for personality.cart.portable module."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from personality.cart.portable import (
    InstallMode,
    Manifest,
    PortableCart,
    _compute_checksum,
    _extract_core,
    _extract_preferences,
)


class TestManifest:
    """Tests for Manifest dataclass."""

    def test_to_dict(self) -> None:
        manifest = Manifest(
            version="1.0",
            cart_name="test",
            created_at="2024-01-01",
            checksums={"core.yml": "abc123"},
            components={"core": True},
        )
        d = manifest.to_dict()
        assert d["version"] == "1.0"
        assert d["cart_name"] == "test"
        assert d["checksums"]["core.yml"] == "abc123"

    def test_from_dict(self) -> None:
        data = {
            "version": "1.0",
            "cart_name": "test",
            "created_at": "2024-01-01",
            "checksums": {},
            "components": {},
        }
        manifest = Manifest.from_dict(data)
        assert manifest.cart_name == "test"
        assert manifest.version == "1.0"


class TestHelpers:
    """Tests for helper functions."""

    def test_compute_checksum(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        checksum = _compute_checksum(test_file)
        assert len(checksum) == 32  # MD5 hex length

    def test_extract_core(self) -> None:
        cart_data = {
            "preferences": {
                "identity": {"name": "Test"},
                "traits": ["friendly"],
                "protocols": ["Protocol 1"],
                "communication_style": {"tone": "formal"},
                "speak": {"voice": "test"},
            }
        }
        core = _extract_core(cart_data)
        assert core["identity"]["name"] == "Test"
        assert "friendly" in core["traits"]
        assert "speak" not in core

    def test_extract_preferences(self) -> None:
        cart_data = {
            "preferences": {
                "identity": {"name": "Test"},
                "speak": {"voice": "test"},
                "overrides": {"key": "value"},
            }
        }
        prefs = _extract_preferences(cart_data)
        assert prefs["speak"]["voice"] == "test"
        assert "identity" not in prefs


class TestPortableCartExport:
    """Tests for PortableCart.export."""

    @pytest.fixture
    def mock_cart_data(self) -> dict:
        return {
            "preferences": {
                "identity": {"name": "Test Bot"},
                "traits": ["helpful"],
                "speak": {"voice": "test_voice"},
            }
        }

    def test_export_creates_directory(self, mock_cart_data: dict, tmp_path: Path) -> None:
        output = tmp_path / "export"
        with (
            patch("personality.cart.portable.load_cart", return_value=mock_cart_data),
            patch("personality.cart.portable.VOICES_DIR", tmp_path / "voices"),
        ):
            PortableCart.export("test", output)

        assert output.exists()
        assert (output / "manifest.json").exists()
        assert (output / "core.yml").exists()
        assert (output / "preferences.yml").exists()

    def test_export_creates_valid_manifest(self, mock_cart_data: dict, tmp_path: Path) -> None:
        output = tmp_path / "export"
        with (
            patch("personality.cart.portable.load_cart", return_value=mock_cart_data),
            patch("personality.cart.portable.VOICES_DIR", tmp_path / "voices"),
        ):
            PortableCart.export("test", output)

        manifest = json.loads((output / "manifest.json").read_text())
        assert manifest["cart_name"] == "test"
        assert "core.yml" in manifest["checksums"]
        assert manifest["components"]["core"] is True

    def test_export_as_zip(self, mock_cart_data: dict, tmp_path: Path) -> None:
        output = tmp_path / "export.zip"
        with (
            patch("personality.cart.portable.load_cart", return_value=mock_cart_data),
            patch("personality.cart.portable.VOICES_DIR", tmp_path / "voices"),
        ):
            PortableCart.export("test", output, as_zip=True)

        assert output.exists()
        assert output.suffix == ".zip"

    def test_export_includes_memories(self, mock_cart_data: dict, tmp_path: Path) -> None:
        output = tmp_path / "export"
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        (memory_dir / "test.db").write_bytes(b"fake db")

        with (
            patch("personality.cart.portable.load_cart", return_value=mock_cart_data),
            patch("personality.cart.portable.MEMORY_DIR", memory_dir),
            patch("personality.cart.portable.VOICES_DIR", tmp_path / "voices"),
        ):
            PortableCart.export("test", output, include_memories=True)

        assert (output / "memory.db").exists()

    def test_export_raises_for_missing_cart(self, tmp_path: Path) -> None:
        with (
            patch("personality.cart.portable.load_cart", return_value=None),
            pytest.raises(ValueError, match="Cart not found"),
        ):
            PortableCart.export("missing", tmp_path / "out")


class TestPortableCartLoad:
    """Tests for PortableCart.load."""

    def test_load_from_directory(self, tmp_path: Path) -> None:
        manifest = {"version": "1.0", "cart_name": "test"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        pcart = PortableCart.load(tmp_path)
        assert pcart.manifest.cart_name == "test"

    def test_load_raises_for_missing_path(self) -> None:
        with pytest.raises(FileNotFoundError):
            PortableCart.load(Path("/nonexistent"))


class TestPortableCartVerify:
    """Tests for PortableCart.verify."""

    def test_verify_valid_files(self, tmp_path: Path) -> None:
        core = tmp_path / "core.yml"
        core.write_text("identity: {}")

        manifest = {
            "version": "1.0",
            "cart_name": "test",
            "checksums": {"core.yml": _compute_checksum(core)},
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        pcart = PortableCart.load(tmp_path)
        results = pcart.verify()
        assert results["core.yml"] == "valid"

    def test_verify_corrupted_file(self, tmp_path: Path) -> None:
        core = tmp_path / "core.yml"
        core.write_text("identity: {}")

        manifest = {
            "version": "1.0",
            "checksums": {"core.yml": "wrong_checksum"},
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        pcart = PortableCart.load(tmp_path)
        results = pcart.verify()
        assert results["core.yml"] == "corrupted"

    def test_verify_missing_file(self, tmp_path: Path) -> None:
        manifest = {
            "version": "1.0",
            "checksums": {"missing.yml": "abc123"},
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        pcart = PortableCart.load(tmp_path)
        results = pcart.verify()
        assert results["missing.yml"] == "missing"


class TestPortableCartInstall:
    """Tests for PortableCart.install."""

    @pytest.fixture
    def pcart_dir(self, tmp_path: Path) -> Path:
        """Create a valid .pcart directory."""
        pcart = tmp_path / "test.pcart"
        pcart.mkdir()

        core = {"identity": {"name": "Test Bot"}, "traits": ["helpful"]}
        prefs = {"speak": {"voice": "test"}}
        manifest = {
            "version": "1.0",
            "cart_name": "test",
            "checksums": {},
            "components": {"core": True, "preferences": True},
        }

        (pcart / "core.yml").write_text(yaml.dump(core))
        (pcart / "preferences.yml").write_text(yaml.dump(prefs))
        (pcart / "manifest.json").write_text(json.dumps(manifest))

        return pcart

    def test_install_safe_mode(self, pcart_dir: Path, tmp_path: Path) -> None:
        carts_dir = tmp_path / "carts"
        with patch("personality.cart.portable.CARTS_DIR", carts_dir):
            pcart = PortableCart.load(pcart_dir)
            stats = pcart.install(mode=InstallMode.SAFE)

        assert stats["cart_name"] == "test"
        assert (carts_dir / "test.yml").exists()

    def test_install_safe_mode_fails_if_exists(self, pcart_dir: Path, tmp_path: Path) -> None:
        carts_dir = tmp_path / "carts"
        carts_dir.mkdir()
        (carts_dir / "test.yml").touch()

        with patch("personality.cart.portable.CARTS_DIR", carts_dir):
            pcart = PortableCart.load(pcart_dir)
            with pytest.raises(ValueError, match="already exists"):
                pcart.install(mode=InstallMode.SAFE)

    def test_install_override_mode(self, pcart_dir: Path, tmp_path: Path) -> None:
        carts_dir = tmp_path / "carts"
        carts_dir.mkdir()
        (carts_dir / "test.yml").write_text("old: data")

        with patch("personality.cart.portable.CARTS_DIR", carts_dir):
            pcart = PortableCart.load(pcart_dir)
            pcart.install(mode=InstallMode.OVERRIDE)

        cart = yaml.safe_load((carts_dir / "test.yml").read_text())
        assert cart["preferences"]["identity"]["name"] == "Test Bot"

    def test_install_dry_run(self, pcart_dir: Path, tmp_path: Path) -> None:
        carts_dir = tmp_path / "carts"
        with patch("personality.cart.portable.CARTS_DIR", carts_dir):
            pcart = PortableCart.load(pcart_dir)
            stats = pcart.install(mode=InstallMode.DRY_RUN)

        assert not carts_dir.exists()
        assert "Dry run" in stats["actions"][0]

    def test_install_with_custom_name(self, pcart_dir: Path, tmp_path: Path) -> None:
        carts_dir = tmp_path / "carts"
        with patch("personality.cart.portable.CARTS_DIR", carts_dir):
            pcart = PortableCart.load(pcart_dir)
            stats = pcart.install(target_name="custom")

        assert stats["cart_name"] == "custom"
        assert (carts_dir / "custom.yml").exists()


class TestInstallMode:
    """Tests for InstallMode enum."""

    def test_modes_exist(self) -> None:
        assert InstallMode.SAFE.value == "safe"
        assert InstallMode.OVERRIDE.value == "override"
        assert InstallMode.MERGE.value == "merge"
        assert InstallMode.DRY_RUN.value == "dry_run"


class TestPortableCartMerge:
    """Tests for merge functionality."""

    @pytest.fixture
    def pcart_with_memory(self, tmp_path: Path) -> Path:
        """Create a .pcart directory with a memory database."""
        import sqlite3

        pcart = tmp_path / "test.pcart"
        pcart.mkdir()

        # Create memory database with a memory
        db_path = pcart / "memory.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY,
                subject TEXT,
                content TEXT,
                source TEXT,
                created_at TEXT
            )
        """)
        conn.execute(
            "INSERT INTO memories (subject, content, source, created_at) VALUES (?, ?, ?, ?)",
            ("test", "imported memory", "import", "2024-01-01"),
        )
        conn.commit()
        conn.close()

        core = {"identity": {"name": "Test"}}
        manifest = {
            "version": "1.0",
            "cart_name": "test",
            "checksums": {},
            "components": {"core": True, "memories": True},
        }

        (pcart / "core.yml").write_text(yaml.dump(core))
        (pcart / "manifest.json").write_text(json.dumps(manifest))

        return pcart

    def test_install_merge_mode_merges_cart_data(self, tmp_path: Path) -> None:
        pcart_dir = tmp_path / "test.pcart"
        pcart_dir.mkdir()

        core = {"identity": {"name": "New Name"}}
        prefs = {"speak": {"voice": "new_voice"}}
        manifest = {"version": "1.0", "cart_name": "test", "checksums": {}, "components": {}}

        (pcart_dir / "core.yml").write_text(yaml.dump(core))
        (pcart_dir / "preferences.yml").write_text(yaml.dump(prefs))
        (pcart_dir / "manifest.json").write_text(json.dumps(manifest))

        # Create existing cart
        carts_dir = tmp_path / "carts"
        carts_dir.mkdir()
        existing = {"preferences": {"identity": {"name": "Old"}, "speak": {"voice": "old_voice"}}}
        (carts_dir / "test.yml").write_text(yaml.dump(existing))

        with patch("personality.cart.portable.CARTS_DIR", carts_dir):
            pcart = PortableCart.load(pcart_dir)
            stats = pcart.install(mode=InstallMode.MERGE)

        assert "Merged" in stats["actions"][0]

        # Check that new identity is used but old speak is preserved
        cart = yaml.safe_load((carts_dir / "test.yml").read_text())
        assert cart["preferences"]["identity"]["name"] == "New Name"
        assert cart["preferences"]["speak"]["voice"] == "old_voice"


class TestPortableCartZip:
    """Tests for ZIP archive handling."""

    def test_load_from_zip(self, tmp_path: Path) -> None:
        import zipfile

        # Create content
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        manifest = {"version": "1.0", "cart_name": "ziptest", "checksums": {}, "components": {}}
        (content_dir / "manifest.json").write_text(json.dumps(manifest))
        (content_dir / "core.yml").write_text("identity: {}")

        # Create ZIP
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for f in content_dir.iterdir():
                zf.write(f, f.name)

        pcart = PortableCart.load(zip_path)
        assert pcart.manifest.cart_name == "ziptest"
        pcart.cleanup()

    def test_cleanup_removes_temp_dir(self, tmp_path: Path) -> None:
        import zipfile

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        manifest = {"version": "1.0", "cart_name": "test", "checksums": {}, "components": {}}
        (content_dir / "manifest.json").write_text(json.dumps(manifest))

        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(content_dir / "manifest.json", "manifest.json")

        pcart = PortableCart.load(zip_path)
        _ = pcart.manifest  # Trigger extraction
        temp_path = pcart._temp_dir

        pcart.cleanup()
        assert temp_path is None or not temp_path.exists()


class TestPortableCartVoice:
    """Tests for voice handling."""

    def test_export_includes_voice(self, tmp_path: Path) -> None:
        cart_data = {"preferences": {"speak": {"voice": "test_voice"}}}
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        (voices_dir / "test_voice.onnx").write_bytes(b"fake model")
        (voices_dir / "test_voice.onnx.json").write_text('{"sample_rate": 22050}')

        output = tmp_path / "export"

        with (
            patch("personality.cart.portable.load_cart", return_value=cart_data),
            patch("personality.cart.portable.VOICES_DIR", voices_dir),
            patch("personality.cart.portable.MEMORY_DIR", tmp_path / "memory"),
        ):
            pcart = PortableCart.export("test", output, include_voice=True)

        assert (output / "test_voice.onnx").exists()
        assert (output / "test_voice.onnx.json").exists()
        assert pcart.manifest.components.get("voice") == "test_voice"
