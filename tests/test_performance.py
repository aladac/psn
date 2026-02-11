"""Performance tests for personality system.

These tests verify acceptable latency for core operations.
Target benchmarks:
- Memory recall: <100ms
- Project search: <200ms
- Embedding generation: measured (depends on Ollama)
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from personality.memory import MemoryStore


class TestMemoryRecallPerformance:
    """Benchmark memory recall operations."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        """Embedder with instant response for performance testing."""
        embedder = MagicMock()
        embedder.dimensions = 384
        embedder.embed.return_value = [0.1] * 384
        return embedder

    @pytest.fixture
    def populated_store(self, mock_embedder: MagicMock) -> MemoryStore:
        """Memory store with 100 memories for benchmarking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path, embedder=mock_embedder)

            # Add 100 diverse memories
            subjects = ["user", "project", "session", "self", "task"]
            for i in range(100):
                subject = f"{subjects[i % 5]}.item{i}"
                content = f"Memory content number {i} with various text"
                store.remember(subject, content)

            yield store
            store.close()

    def test_recall_latency_under_100ms(self, populated_store: MemoryStore) -> None:
        """Recall should complete in under 100ms with 100 memories."""
        start = time.perf_counter()
        _ = populated_store.recall("memory content", k=10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Recall took {elapsed_ms:.1f}ms, expected <100ms"

    def test_recall_scales_with_k(self, populated_store: MemoryStore) -> None:
        """Recall time should not scale dramatically with k."""
        # k=5
        start = time.perf_counter()
        _ = populated_store.recall("content", k=5)
        time_k5 = (time.perf_counter() - start) * 1000

        # k=20
        start = time.perf_counter()
        _ = populated_store.recall("content", k=20)
        time_k20 = (time.perf_counter() - start) * 1000

        # k=20 should not be more than 3x slower than k=5
        assert time_k20 < time_k5 * 3, f"k=20 ({time_k20:.1f}ms) too slow vs k=5 ({time_k5:.1f}ms)"

    def test_list_all_latency(self, populated_store: MemoryStore) -> None:
        """list_all should complete quickly."""
        start = time.perf_counter()
        memories = populated_store.list_all()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(memories) == 100
        assert elapsed_ms < 50, f"list_all took {elapsed_ms:.1f}ms, expected <50ms"


class TestProjectSearchPerformance:
    """Benchmark project search operations."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 384
        embedder.embed.return_value = [0.1] * 384
        embedder.embed_batch.return_value = [[0.1] * 384] * 50
        return embedder

    def test_search_latency_under_200ms(self, mock_embedder: MagicMock) -> None:
        """Project search should complete in under 200ms."""
        from unittest.mock import patch

        from personality.index import get_indexer

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create 20 Python files
            for i in range(20):
                (project_dir / f"module{i}.py").write_text(f'''
def function_{i}():
    """Function number {i}."""
    return {i}


class Class{i}:
    """Class number {i}."""
    pass
''')

            with patch("personality.index.indexer.get_embedder", return_value=mock_embedder):
                indexer = get_indexer(project_dir)
                indexer.index()

                start = time.perf_counter()
                _ = indexer.search("function class", k=10)
                elapsed_ms = (time.perf_counter() - start) * 1000

                indexer.close()

            assert elapsed_ms < 200, f"Search took {elapsed_ms:.1f}ms, expected <200ms"


class TestLargeMemoryDatabase:
    """Test with large memory databases."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 384
        embedder.embed.return_value = [0.1] * 384
        return embedder

    def test_recall_with_1000_memories(self, mock_embedder: MagicMock) -> None:
        """Recall should still be fast with 1000 memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "large.db"
            store = MemoryStore(db_path, embedder=mock_embedder)

            # Add 1000 memories
            for i in range(1000):
                store.remember(f"item.{i}", f"Content for memory {i}")

            # Benchmark recall
            start = time.perf_counter()
            results = store.recall("content memory", k=10)
            elapsed_ms = (time.perf_counter() - start) * 1000

            store.close()

            assert len(results) == 10
            # Should still be under 200ms even with 1000 memories
            assert elapsed_ms < 200, f"Recall took {elapsed_ms:.1f}ms with 1000 memories"

    def test_consolidation_performance(self, mock_embedder: MagicMock) -> None:
        """Consolidation should complete in reasonable time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "consolidate.db"
            store = MemoryStore(db_path, embedder=mock_embedder)

            # Add 100 memories with same embedding (will all be similar)
            for i in range(100):
                store.remember(f"similar.{i}", f"Similar content {i}")

            start = time.perf_counter()
            _ = store.consolidate(threshold=0.99)
            elapsed_ms = (time.perf_counter() - start) * 1000

            store.close()

            # Consolidation with 100 items should be under 500ms
            assert elapsed_ms < 500, f"Consolidation took {elapsed_ms:.1f}ms"


class TestDatabaseOperations:
    """Test raw database operation performance."""

    def test_sqlite_vec_query_performance(self) -> None:
        """Direct sqlite-vec query should be fast."""
        import sqlite3
        import struct

        import sqlite_vec

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vec_test.db"
            conn = sqlite3.connect(str(db_path))
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)

            # Create table
            conn.execute("CREATE VIRTUAL TABLE test_vec USING vec0(embedding float[384])")

            # Insert 500 vectors
            def serialize(vec: list) -> bytes:
                return struct.pack(f"{len(vec)}f", *vec)

            for i in range(500):
                vec = [float(i % 10) / 10 + j * 0.001 for j in range(384)]
                conn.execute("INSERT INTO test_vec (rowid, embedding) VALUES (?, ?)", (i, serialize(vec)))
            conn.commit()

            # Benchmark similarity search
            query_vec = serialize([0.5] * 384)
            start = time.perf_counter()
            results = conn.execute(
                """
                SELECT rowid, distance
                FROM test_vec
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT 10
                """,
                (query_vec,),
            ).fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000

            conn.close()

            assert len(results) == 10
            # Raw sqlite-vec should be very fast
            assert elapsed_ms < 50, f"Vec search took {elapsed_ms:.1f}ms"

    def test_fts5_query_performance(self) -> None:
        """FTS5 full-text search should be fast."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "fts_test.db"
            conn = sqlite3.connect(str(db_path))

            # Create FTS table
            conn.execute("""
                CREATE VIRTUAL TABLE test_fts USING fts5(
                    content, tokenize='porter'
                )
            """)

            # Insert 500 documents
            for i in range(500):
                conn.execute(
                    "INSERT INTO test_fts (content) VALUES (?)", (f"Document {i} with various words and content text",)
                )
            conn.commit()

            # Benchmark FTS search
            start = time.perf_counter()
            results = conn.execute("SELECT rowid FROM test_fts WHERE test_fts MATCH 'content text' LIMIT 10").fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000

            conn.close()

            assert len(results) == 10
            # FTS5 should be very fast
            assert elapsed_ms < 20, f"FTS search took {elapsed_ms:.1f}ms"
