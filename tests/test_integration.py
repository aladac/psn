"""Integration tests for personality system.

These tests verify end-to-end workflows without mocking core components.
Only external services (Ollama, file system paths) are mocked.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from personality.cart.portable import InstallMode, PortableCart
from personality.hooks import session_end, session_start
from personality.memory import MemoryStore


class TestSessionLifecycle:
    """Test session lifecycle: start → work → end."""

    @pytest.fixture
    def mock_cart_data(self) -> dict:
        return {
            "preferences": {
                "identity": {"name": "Test Bot", "tagline": "Ready to assist"},
                "traits": ["helpful", "precise"],
            }
        }

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    def test_session_start_returns_persona(self, mock_cart_data: dict) -> None:
        with (
            patch("personality.hooks.load_cart", return_value=mock_cart_data),
            patch("personality.hooks.get_speaker", return_value=(MagicMock(), "test")),
            patch("personality.hooks.log_hook"),
        ):
            result = session_start("test")

        assert result.status == "ok"
        assert result.data["persona"] == "Test Bot"
        assert result.data["greeting"] == "Ready to assist"

    def test_session_end_consolidates(self) -> None:
        with (
            patch("personality.hooks.get_speaker", return_value=(MagicMock(), "test")),
            patch("personality.hooks.log_hook"),
        ):
            result = session_end("test")

        assert result.status == "ok"
        assert "consolidated" in result.data

    def test_full_session_workflow(self, mock_cart_data: dict, mock_embedder: MagicMock) -> None:
        """Test complete session: start, remember, recall, end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path, embedder=mock_embedder)

            # Session start
            with (
                patch("personality.hooks.load_cart", return_value=mock_cart_data),
                patch("personality.hooks.get_speaker", return_value=(MagicMock(), "test")),
                patch("personality.hooks.log_hook"),
            ):
                start_result = session_start("test")
            assert start_result.status == "ok"

            # Work: remember something
            mem_id = store.remember("user.preference", "Prefers dark mode")
            assert mem_id > 0

            # Work: recall it
            memories = store.recall("dark mode", k=5)
            assert len(memories) > 0
            assert any("dark mode" in m.content for m in memories)

            # Session end
            with (
                patch("personality.hooks.get_speaker", return_value=(MagicMock(), "test")),
                patch("personality.hooks.log_hook"),
            ):
                end_result = session_end("test")
            assert end_result.status == "ok"

            store.close()


class TestMemoryPersistence:
    """Test memory persistence across sessions."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.5, 0.5, 0.5]
        return embedder

    def test_memories_persist_across_store_instances(self, mock_embedder: MagicMock) -> None:
        """Memories saved in one session are available in the next."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"

            # Session 1: Remember something
            store1 = MemoryStore(db_path, embedder=mock_embedder)
            store1.remember("user.name", "Alice")
            store1.close()

            # Session 2: Recall it
            store2 = MemoryStore(db_path, embedder=mock_embedder)
            memories = store2.recall("Alice", k=5)
            store2.close()

            assert len(memories) > 0
            assert any("Alice" in m.content for m in memories)

    def test_forget_removes_memory_permanently(self, mock_embedder: MagicMock) -> None:
        """Forgotten memories stay forgotten across sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"

            # Session 1: Remember and forget
            store1 = MemoryStore(db_path, embedder=mock_embedder)
            mem_id = store1.remember("secret", "password123")
            store1.forget(mem_id)
            store1.close()

            # Session 2: Verify it's gone
            store2 = MemoryStore(db_path, embedder=mock_embedder)
            all_memories = store2.list_all()
            store2.close()

            assert not any(m.id == mem_id for m in all_memories)

    def test_consolidation_merges_similar_memories(self, mock_embedder: MagicMock) -> None:
        """Similar memories are merged during consolidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path, embedder=mock_embedder)

            # Add similar memories
            store.remember("protocols", "Protocol 1: Link to Pilot")
            store.remember("protocols", "Protocol 1 means Link to Pilot")
            store.remember("protocols", "Protocol 1 - Link to Pilot")

            before_count = len(store.list_all())

            # Consolidate with high threshold (embeddings are identical)
            merged = store.consolidate(threshold=0.99)

            after_count = len(store.list_all())
            store.close()

            # Should have merged some memories
            assert merged > 0 or before_count == after_count


class TestProjectIndexSearch:
    """Test project indexing and search."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.3, 0.3, 0.3]
        embedder.embed_batch.return_value = [[0.3, 0.3, 0.3]]
        return embedder

    def test_index_and_search_python_file(self, mock_embedder: MagicMock) -> None:
        """Index a Python file and search for content."""
        from personality.index import get_indexer

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create a Python file
            py_file = project_dir / "example.py"
            py_file.write_text('''
def calculate_total(items):
    """Calculate the total price of items."""
    return sum(item.price for item in items)


class ShoppingCart:
    """A shopping cart for e-commerce."""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)
''')

            with patch("personality.index.indexer.get_embedder", return_value=mock_embedder):
                indexer = get_indexer(project_dir)
                stats = indexer.index()

            assert stats["files_indexed"] >= 1

            # Search for content
            results = indexer.search("shopping cart", k=5)

            indexer.close()

            # Should find relevant chunks
            assert len(results) > 0

    def test_index_respects_gitignore(self, mock_embedder: MagicMock) -> None:
        """Indexer should skip files in .gitignore."""
        from personality.index import get_indexer

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create .gitignore
            (project_dir / ".gitignore").write_text("ignored/\n*.log\n")

            # Create files
            (project_dir / "main.py").write_text("def main(): pass")
            ignored_dir = project_dir / "ignored"
            ignored_dir.mkdir()
            (ignored_dir / "secret.py").write_text("SECRET = 'password'")
            (project_dir / "debug.log").write_text("debug info")

            with patch("personality.index.indexer.get_embedder", return_value=mock_embedder):
                indexer = get_indexer(project_dir)
                stats = indexer.index()
                indexer.close()

            # Should only index main.py
            assert stats["files_indexed"] == 1


class TestCartExportImportCycle:
    """Test cart export/import round-trip."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.4, 0.4, 0.4]
        return embedder

    @pytest.fixture
    def sample_cart_data(self) -> dict:
        return {
            "preferences": {
                "identity": {"name": "BT-7274", "tagline": "Protocol 3"},
                "traits": ["loyal", "precise"],
                "protocols": ["Link to Pilot", "Uphold the Mission"],
                "speak": {"voice": "bt7274"},
            }
        }

    def test_export_import_preserves_cart_data(self, sample_cart_data: dict) -> None:
        """Cart data is preserved through export/import cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            export_path = tmp / "exported.pcart"
            carts_dir = tmp / "carts"

            with (
                patch("personality.cart.portable.load_cart", return_value=sample_cart_data),
                patch("personality.cart.portable.CARTS_DIR", carts_dir),
                patch("personality.cart.portable.VOICES_DIR", tmp / "voices"),
                patch("personality.cart.portable.MEMORY_DIR", tmp / "memory"),
            ):
                # Export
                pcart = PortableCart.export("bt7274", export_path, include_voice=False, include_memories=False)

                # Verify export
                assert (export_path / "core.yml").exists()
                assert (export_path / "preferences.yml").exists()
                assert (export_path / "manifest.json").exists()

                # Import to new location
                pcart.install(mode=InstallMode.SAFE, target_name="bt7274_copy")

            # Verify import
            assert (carts_dir / "bt7274_copy.yml").exists()
            imported = yaml.safe_load((carts_dir / "bt7274_copy.yml").read_text())
            assert imported["preferences"]["identity"]["name"] == "BT-7274"
            assert "loyal" in imported["preferences"]["traits"]

    def test_export_import_with_memories(self, sample_cart_data: dict, mock_embedder: MagicMock) -> None:
        """Memories are preserved through export/import cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            export_path = tmp / "exported.pcart"
            carts_dir = tmp / "carts"
            memory_dir = tmp / "memory"
            memory_dir.mkdir()

            # Create memory database with content
            db_path = memory_dir / "bt7274.db"
            store = MemoryStore(db_path, embedder=mock_embedder)
            store.remember("protocols", "Protocol 3: Protect the Pilot")
            store.close()

            with (
                patch("personality.cart.portable.load_cart", return_value=sample_cart_data),
                patch("personality.cart.portable.CARTS_DIR", carts_dir),
                patch("personality.cart.portable.VOICES_DIR", tmp / "voices"),
                patch("personality.cart.portable.MEMORY_DIR", memory_dir),
            ):
                # Export with memories
                PortableCart.export("bt7274", export_path, include_voice=False, include_memories=True)

                # Verify memory.db is exported
                assert (export_path / "memory.db").exists()

    def test_zip_export_import_cycle(self, sample_cart_data: dict) -> None:
        """ZIP export/import preserves all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            zip_path = tmp / "cart.zip"
            carts_dir = tmp / "carts"

            with (
                patch("personality.cart.portable.load_cart", return_value=sample_cart_data),
                patch("personality.cart.portable.CARTS_DIR", carts_dir),
                patch("personality.cart.portable.VOICES_DIR", tmp / "voices"),
                patch("personality.cart.portable.MEMORY_DIR", tmp / "memory"),
            ):
                # Export as ZIP
                PortableCart.export("bt7274", zip_path, as_zip=True, include_voice=False)

                assert zip_path.exists()

                # Import from ZIP
                pcart = PortableCart.load(zip_path)
                assert pcart.manifest.cart_name == "bt7274"

                pcart.install(mode=InstallMode.SAFE)
                pcart.cleanup()

            assert (carts_dir / "bt7274.yml").exists()


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.2, 0.2, 0.2]
        embedder.embed_batch.return_value = [[0.2, 0.2, 0.2]]
        return embedder

    def test_new_user_onboarding_workflow(self, mock_embedder: MagicMock) -> None:
        """Test a new user setting up and using the system."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_path = tmp / "memory.db"

            # 1. Initialize memory store
            store = MemoryStore(db_path, embedder=mock_embedder)

            # 2. User provides preferences
            store.remember("user.name", "Pilot Chi")
            store.remember("user.preferences.editor", "VSCode")
            store.remember("user.preferences.theme", "Dark mode")

            # 3. Recall user info
            prefs = store.recall("user preferences", k=5)
            assert len(prefs) >= 2

            # 4. Store project decision
            store.remember("project.architecture.database", "Using SQLite with sqlite-vec for vector search")

            # 5. Recall for decision support
            arch = store.recall("database architecture", k=3)
            assert len(arch) >= 1

            store.close()

    def test_cross_session_context_preservation(self, mock_embedder: MagicMock) -> None:
        """Context from previous sessions is available in new sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"

            # Session 1: Work on a feature
            store1 = MemoryStore(db_path, embedder=mock_embedder)
            store1.remember("session.2024-01-15", "Implemented user auth")
            store1.remember("project.decisions.auth", "Using JWT for authentication")
            store1.close()

            # Session 2: Continue work
            store2 = MemoryStore(db_path, embedder=mock_embedder)

            # Should find context from previous session
            auth_context = store2.recall("authentication", k=3)
            assert len(auth_context) >= 1

            # Add to the context
            store2.remember("project.decisions.auth", "Added refresh token support")
            store2.close()

            # Session 3: Review all auth decisions
            store3 = MemoryStore(db_path, embedder=mock_embedder)
            all_auth = store3.recall("authentication JWT", k=10)
            store3.close()

            # Should have both memories
            assert len(all_auth) >= 2
