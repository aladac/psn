"""Tests for personality.memory.store and schema modules."""

import struct
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personality.memory.schema import (
    FTS_SYNC_TRIGGERS,
    SCHEMA_VERSION,
    get_schema_sql,
    init_database,
)
from personality.memory.store import (
    CONSOLIDATE_THRESHOLD,
    DEFAULT_K,
    DEFAULT_THRESHOLD,
    Memory,
    MemoryStore,
    serialize_f32,
)


class TestSerializeF32:
    """Tests for serialize_f32 helper."""

    def test_serialize_empty(self) -> None:
        result = serialize_f32([])
        assert result == b""

    def test_serialize_single(self) -> None:
        result = serialize_f32([1.0])
        assert len(result) == 4
        assert struct.unpack("f", result)[0] == pytest.approx(1.0)

    def test_serialize_multiple(self) -> None:
        vec = [0.1, 0.2, 0.3]
        result = serialize_f32(vec)
        assert len(result) == 12
        unpacked = struct.unpack("3f", result)
        for i, val in enumerate(unpacked):
            assert val == pytest.approx(vec[i], rel=1e-5)


class TestSchema:
    """Tests for database schema."""

    def test_schema_version_constant(self) -> None:
        assert SCHEMA_VERSION == 1

    def test_get_schema_sql_includes_dimensions(self) -> None:
        sql = get_schema_sql(768)
        assert "FLOAT[768]" in sql
        assert "memories" in sql
        assert "memories_vec" in sql
        assert "memories_fts" in sql

    def test_fts_sync_triggers_defined(self) -> None:
        assert "memories_ai" in FTS_SYNC_TRIGGERS
        assert "memories_ad" in FTS_SYNC_TRIGGERS
        assert "memories_au" in FTS_SYNC_TRIGGERS

    def test_init_database_creates_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_database(db_path, 3)

            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]

            assert "memories" in table_names
            assert "schema_version" in table_names
            conn.close()


class TestMemoryDataclass:
    """Tests for Memory dataclass."""

    def test_memory_creation(self) -> None:
        mem = Memory(
            id=1,
            subject="test",
            content="content",
            source="manual",
            created_at="2024-01-01",
            accessed_at="2024-01-01",
            access_count=0,
        )
        assert mem.id == 1
        assert mem.score == 0.0

    def test_memory_with_score(self) -> None:
        mem = Memory(
            id=1,
            subject="test",
            content="content",
            source="manual",
            created_at="2024-01-01",
            accessed_at="2024-01-01",
            access_count=0,
            score=0.85,
        )
        assert mem.score == 0.85


class TestMemoryStore:
    """Tests for MemoryStore class."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    @pytest.fixture
    def store(self, mock_embedder: MagicMock) -> MemoryStore:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path, embedder=mock_embedder)
            yield store
            store.close()

    def test_init_creates_store(self, store: MemoryStore) -> None:
        assert store.db_path.name == "memory.db"
        assert store.embedder is not None

    def test_conn_property_lazy_init(self, store: MemoryStore) -> None:
        assert store._conn is None
        _ = store.conn
        assert store._conn is not None

    def test_remember_stores_memory(self, store: MemoryStore) -> None:
        mem_id = store.remember("protocols", "Protocol 1: Link to Pilot")
        assert mem_id == 1

        row = store.conn.execute("SELECT * FROM memories WHERE id = 1").fetchone()
        assert row is not None
        assert row[1] == "protocols"
        assert row[2] == "Protocol 1: Link to Pilot"

    def test_remember_with_source(self, store: MemoryStore) -> None:
        mem_id = store.remember("test", "content", source="learned")
        row = store.conn.execute("SELECT source FROM memories WHERE id = ?", (mem_id,)).fetchone()
        assert row[0] == "learned"

    def test_remember_creates_embedding(self, store: MemoryStore, mock_embedder: MagicMock) -> None:
        store.remember("test", "content")
        mock_embedder.embed.assert_called_once_with("test: content")

    def test_list_all_empty(self, store: MemoryStore) -> None:
        assert store.list_all() == []

    def test_list_all_returns_memories(self, store: MemoryStore) -> None:
        store.remember("subject1", "content1")
        store.remember("subject2", "content2")

        memories = store.list_all()
        assert len(memories) == 2
        assert all(isinstance(m, Memory) for m in memories)

    def test_forget_removes_memory(self, store: MemoryStore) -> None:
        mem_id = store.remember("test", "to delete")
        assert store.forget(mem_id) is True

        row = store.conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        assert row is None

    def test_forget_nonexistent_returns_false(self, store: MemoryStore) -> None:
        assert store.forget(999) is False

    def test_recall_empty_store(self, store: MemoryStore) -> None:
        result = store.recall("anything")
        assert result == []

    @patch("personality.memory.store.MemoryStore._cosine_similarity")
    def test_recall_finds_memory(self, mock_sim: MagicMock, store: MemoryStore) -> None:
        mock_sim.return_value = 0.9
        store.remember("protocols", "Protocol 1: Link to Pilot")

        results = store.recall("protocol")
        assert len(results) >= 1
        assert results[0].subject == "protocols"

    def test_recall_updates_access_count(self, store: MemoryStore) -> None:
        store.remember("test", "content")
        store.recall("test")

        row = store.conn.execute("SELECT access_count FROM memories WHERE id = 1").fetchone()
        assert row[0] == 1

    def test_close_releases_connection(self, store: MemoryStore) -> None:
        _ = store.conn
        assert store._conn is not None
        store.close()
        assert store._conn is None

    def test_cosine_similarity_identical(self, store: MemoryStore) -> None:
        vec = [0.5, 0.5, 0.5]
        sim = store._cosine_similarity(vec, vec)
        assert sim == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self, store: MemoryStore) -> None:
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        sim = store._cosine_similarity(a, b)
        assert sim == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self, store: MemoryStore) -> None:
        a = [0.0, 0.0, 0.0]
        b = [1.0, 1.0, 1.0]
        sim = store._cosine_similarity(a, b)
        assert sim == 0.0

    def test_recall_wildcard_returns_all(self, store: MemoryStore) -> None:
        store.remember("topic1", "First memory")
        store.remember("topic2", "Second memory")
        store.remember("topic3", "Third memory")

        results = store.recall("*")
        assert len(results) == 3

    def test_recall_all_keyword_returns_all(self, store: MemoryStore) -> None:
        store.remember("topic1", "First memory")
        store.remember("topic2", "Second memory")

        results = store.recall("all")
        assert len(results) == 2

    def test_recall_empty_string_returns_all(self, store: MemoryStore) -> None:
        store.remember("topic1", "First memory")

        results = store.recall("")
        assert len(results) == 1

    def test_recall_wildcard_respects_limit(self, store: MemoryStore) -> None:
        for i in range(10):
            store.remember(f"topic{i}", f"Memory {i}")

        results = store.recall("*", k=3)
        assert len(results) == 3

    def test_recall_special_chars_dont_crash(self, store: MemoryStore) -> None:
        store.remember("test", "Content with special chars")

        # These would crash FTS5 without escaping
        for query in ['"quoted"', "paren(heses)", "colon:sep", "plus+"]:
            results = store.recall(query)
            assert isinstance(results, list)


class TestMemoryStoreConsolidate:
    """Tests for MemoryStore.consolidate method."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        return embedder

    @pytest.fixture
    def store(self, mock_embedder: MagicMock) -> MemoryStore:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path, embedder=mock_embedder)
            yield store
            store.close()

    def test_consolidate_empty_store(self, store: MemoryStore) -> None:
        result = store.consolidate()
        assert result == 0

    def test_consolidate_single_memory(self, store: MemoryStore, mock_embedder: MagicMock) -> None:
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        store.remember("test", "content")
        result = store.consolidate()
        assert result == 0

    def test_consolidate_merges_similar(self, store: MemoryStore, mock_embedder: MagicMock) -> None:
        mock_embedder.embed.return_value = [0.5, 0.5, 0.5]
        store.remember("protocols", "Protocol 1")
        store.remember("protocols", "Protocol 1 detail")

        merged = store.consolidate(threshold=0.99)
        assert merged == 1
        assert len(store.list_all()) == 1

    def test_consolidate_preserves_different_subjects(self, store: MemoryStore, mock_embedder: MagicMock) -> None:
        mock_embedder.embed.return_value = [0.5, 0.5, 0.5]
        store.remember("protocols", "Protocol 1")
        store.remember("different", "Protocol 1")

        merged = store.consolidate()
        assert merged == 0
        assert len(store.list_all()) == 2


class TestConstants:
    """Tests for module constants."""

    def test_default_k(self) -> None:
        assert DEFAULT_K == 5

    def test_default_threshold(self) -> None:
        assert DEFAULT_THRESHOLD == 0.7

    def test_consolidate_threshold(self) -> None:
        assert CONSOLIDATE_THRESHOLD == 0.92
