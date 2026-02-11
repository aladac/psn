"""Tests for personality.index module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personality.index.chunker import (
    CHUNK_OVERLAP,
    CHUNK_WINDOW_SIZE,
    Chunk,
    chunk_file,
    detect_language,
    sliding_window_chunks,
)
from personality.index.indexer import (
    CODE_EXTENSIONS,
    IGNORE_PATTERNS,
    ProjectIndexer,
    SearchResult,
    get_indexer,
    list_indexed_projects,
)
from personality.index.schema import (
    INDEX_FTS_TRIGGERS,
    INDEX_SCHEMA_VERSION,
    get_index_schema_sql,
    init_index_database,
)


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_chunk_creation(self) -> None:
        chunk = Chunk(
            chunk_type="function",
            name="test_func",
            content="def test(): pass",
            start_line=1,
            end_line=1,
        )
        assert chunk.chunk_type == "function"
        assert chunk.name == "test_func"


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_python(self) -> None:
        assert detect_language(Path("test.py")) == "python"

    def test_ruby(self) -> None:
        assert detect_language(Path("test.rb")) == "ruby"

    def test_rust(self) -> None:
        assert detect_language(Path("test.rs")) == "rust"

    def test_javascript(self) -> None:
        assert detect_language(Path("test.js")) == "javascript"

    def test_typescript(self) -> None:
        assert detect_language(Path("test.ts")) == "typescript"

    def test_unknown(self) -> None:
        assert detect_language(Path("test.txt")) is None


class TestSlidingWindowChunks:
    """Tests for sliding_window_chunks function."""

    def test_empty_lines(self) -> None:
        result = sliding_window_chunks([], "test")
        assert result == []

    def test_single_chunk(self) -> None:
        lines = ["line1", "line2", "line3"]
        result = sliding_window_chunks(lines, "test", window_size=10)
        assert len(result) == 1
        assert result[0].chunk_type == "window"

    def test_multiple_chunks(self) -> None:
        lines = [f"line{i}" for i in range(100)]
        result = sliding_window_chunks(lines, "test", window_size=20, overlap=5)
        assert len(result) > 1

    def test_overlap(self) -> None:
        lines = [f"line{i}" for i in range(30)]
        result = sliding_window_chunks(lines, "test", window_size=20, overlap=10)
        # First chunk: 0-20, second chunk: 10-30
        assert len(result) == 2

    def test_skips_empty_content(self) -> None:
        lines = ["", "", ""]
        result = sliding_window_chunks(lines, "test")
        assert result == []


class TestChunkFile:
    """Tests for chunk_file function."""

    def test_chunks_python_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    print('hello')\n")
            f.flush()
            path = Path(f.name)

        chunks = chunk_file(path)
        path.unlink()

        assert len(chunks) > 0

    def test_falls_back_to_window_for_unknown_language(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line1\nline2\nline3\n")
            f.flush()
            path = Path(f.name)

        chunks = chunk_file(path)
        path.unlink()

        assert len(chunks) > 0
        assert chunks[0].chunk_type == "window"


class TestIndexSchema:
    """Tests for index schema."""

    def test_schema_version(self) -> None:
        assert INDEX_SCHEMA_VERSION == 1

    def test_get_schema_sql_includes_dimensions(self) -> None:
        sql = get_index_schema_sql(768)
        assert "FLOAT[768]" in sql
        assert "chunks" in sql
        assert "chunks_vec" in sql
        assert "files" in sql

    def test_fts_triggers_defined(self) -> None:
        assert "chunks_ai" in INDEX_FTS_TRIGGERS

    def test_init_creates_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_index_database(str(db_path), 3)

            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]

            assert "chunks" in table_names
            assert "files" in table_names
            conn.close()


class TestProjectIndexer:
    """Tests for ProjectIndexer class."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    @pytest.fixture
    def project_dir(self) -> Path:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "test_project"
            project.mkdir()
            (project / "main.py").write_text("def main():\n    pass\n")
            (project / "utils.py").write_text("def helper():\n    return 1\n")
            yield project

    @pytest.fixture
    def indexer(self, project_dir: Path, mock_embedder: MagicMock) -> ProjectIndexer:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("personality.index.indexer.INDEX_DIR", Path(tmpdir)),
        ):
            idx = ProjectIndexer(project_dir, embedder=mock_embedder)
            yield idx
            idx.close()

    def test_db_path_is_derived_from_project(self, indexer: ProjectIndexer) -> None:
        assert indexer.db_path.suffix == ".db"

    def test_index_returns_stats(self, indexer: ProjectIndexer) -> None:
        stats = indexer.index()
        assert "files_indexed" in stats
        assert "chunks_created" in stats
        assert stats["files_indexed"] == 2

    def test_index_force_reindexes(self, indexer: ProjectIndexer) -> None:
        indexer.index()
        stats = indexer.index(force=True)
        assert stats["files_indexed"] == 2
        assert stats["files_skipped"] == 0

    def test_index_skips_unchanged(self, indexer: ProjectIndexer) -> None:
        indexer.index()
        stats = indexer.index()
        assert stats["files_skipped"] == 2
        assert stats["files_indexed"] == 0

    def test_status_returns_info(self, indexer: ProjectIndexer) -> None:
        indexer.index()
        status = indexer.status()
        assert status["file_count"] == 2
        assert status["chunk_count"] > 0

    def test_set_and_get_summary(self, indexer: ProjectIndexer) -> None:
        indexer.set_summary("Test project summary")
        assert indexer.get_summary() == "Test project summary"

    def test_search_returns_results(self, indexer: ProjectIndexer, mock_embedder: MagicMock) -> None:
        indexer.index()
        results = indexer.search("main function")
        assert isinstance(results, list)

    def test_close_releases_connection(self, indexer: ProjectIndexer) -> None:
        _ = indexer.conn
        assert indexer._conn is not None
        indexer.close()
        assert indexer._conn is None


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_creation(self) -> None:
        result = SearchResult(
            file_path="test.py",
            chunk_type="function",
            name="test",
            content="def test(): pass",
            start_line=1,
            end_line=1,
            score=0.9,
        )
        assert result.file_path == "test.py"
        assert result.score == 0.9


class TestGetIndexer:
    """Tests for get_indexer function."""

    def test_returns_indexer_for_cwd(self) -> None:
        indexer = get_indexer()
        assert indexer.project_path == Path.cwd().resolve()

    def test_returns_indexer_for_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = get_indexer(Path(tmpdir))
            assert indexer.project_path == Path(tmpdir).resolve()


class TestListIndexedProjects:
    """Tests for list_indexed_projects function."""

    def test_returns_empty_when_no_registry(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("personality.index.indexer.REGISTRY_FILE", Path(tmpdir) / "none.json"),
        ):
            result = list_indexed_projects()
        assert result == {}


class TestConstants:
    """Tests for module constants."""

    def test_chunk_window_size(self) -> None:
        assert CHUNK_WINDOW_SIZE == 50

    def test_chunk_overlap(self) -> None:
        assert CHUNK_OVERLAP == 10

    def test_ignore_patterns(self) -> None:
        assert ".git" in IGNORE_PATTERNS
        assert "node_modules" in IGNORE_PATTERNS

    def test_code_extensions(self) -> None:
        assert ".py" in CODE_EXTENSIONS
        assert ".js" in CODE_EXTENSIONS


class TestProjectIndexerEdgeCases:
    """Additional edge case tests for ProjectIndexer."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    def test_discover_respects_gitignore(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "main.py").write_text("pass")
            (project / "ignored.py").write_text("pass")
            (project / ".gitignore").write_text("ignored.py\n")

            indexer = ProjectIndexer(project, embedder=mock_embedder)
            files = indexer._discover_files()
            indexer.close()

            file_names = [f.name for f in files]
            assert "main.py" in file_names
            assert "ignored.py" not in file_names

    def test_discover_skips_ignored_dirs(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "src").mkdir()
            (project / "src" / "main.py").write_text("pass")
            (project / "node_modules").mkdir()
            (project / "node_modules" / "lib.py").write_text("pass")

            indexer = ProjectIndexer(project, embedder=mock_embedder)
            files = indexer._discover_files()
            indexer.close()

            paths = [str(f) for f in files]
            assert any("main.py" in p for p in paths)
            assert not any("node_modules" in p for p in paths)

    def test_compute_hash(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            test_file = project / "test.py"
            test_file.write_text("hello")

            indexer = ProjectIndexer(project, embedder=mock_embedder)
            hash1 = indexer._compute_hash(test_file)

            test_file.write_text("changed")
            hash2 = indexer._compute_hash(test_file)

            indexer.close()

            assert hash1 != hash2

    def test_is_current_false_when_not_indexed(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            indexer = ProjectIndexer(project, embedder=mock_embedder)
            _ = indexer.conn  # Initialize

            assert not indexer._is_current("nonexistent.py", "abc123")
            indexer.close()

    def test_summary_none_when_not_set(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            indexer = ProjectIndexer(project, embedder=mock_embedder)
            _ = indexer.conn

            assert indexer.get_summary() is None
            indexer.close()

    def test_search_empty_index(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            indexer = ProjectIndexer(project, embedder=mock_embedder)
            _ = indexer.conn

            results = indexer.search("anything")
            assert results == []
            indexer.close()
