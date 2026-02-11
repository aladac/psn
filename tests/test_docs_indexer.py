"""Tests for personality.docs module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personality.docs.chunker import (
    DocChunk,
    chunk_markdown,
    extract_code_blocks,
    parse_frontmatter,
)
from personality.docs.indexer import (
    DocIndexer,
    DocSearchResult,
    get_doc_indexer,
)
from personality.docs.schema import (
    DOC_FTS_TRIGGERS,
    DOC_SCHEMA_VERSION,
    get_doc_schema_sql,
    init_doc_database,
)


class TestDocChunk:
    """Tests for DocChunk dataclass."""

    def test_creation(self) -> None:
        chunk = DocChunk(
            chunk_type="section",
            heading="Introduction",
            content="Hello world",
            start_line=1,
            end_line=5,
        )
        assert chunk.chunk_type == "section"
        assert chunk.heading == "Introduction"

    def test_default_metadata(self) -> None:
        chunk = DocChunk(
            chunk_type="section",
            heading=None,
            content="content",
            start_line=1,
            end_line=1,
        )
        assert chunk.metadata == {}


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parses_valid_frontmatter(self) -> None:
        content = """---
source: https://example.com
fetched: 2024-01-15
---
# Title

Content here.
"""
        metadata, remaining = parse_frontmatter(content)
        assert metadata["source"] == "https://example.com"
        assert "fetched" in metadata
        assert "# Title" in remaining

    def test_no_frontmatter(self) -> None:
        content = "# Just a heading\n\nSome content."
        metadata, remaining = parse_frontmatter(content)
        assert metadata == {}
        assert remaining == content

    def test_invalid_yaml(self) -> None:
        content = """---
invalid: [unclosed
---
# Title
"""
        metadata, remaining = parse_frontmatter(content)
        assert metadata == {}
        assert content == remaining


class TestChunkMarkdown:
    """Tests for chunk_markdown function."""

    def test_chunks_simple_document(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Title

## Section One

Content for section one.

## Section Two

Content for section two.
""")
            f.flush()
            path = Path(f.name)

        chunks = chunk_markdown(path)
        path.unlink()

        assert len(chunks) >= 2
        headings = [c.heading for c in chunks if c.heading]
        assert "Section One" in headings or "Title" in headings

    def test_extracts_frontmatter_chunk(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""---
source: https://example.com
---
# Content
""")
            f.flush()
            path = Path(f.name)

        chunks = chunk_markdown(path)
        path.unlink()

        fm_chunks = [c for c in chunks if c.chunk_type == "frontmatter"]
        assert len(fm_chunks) == 1
        assert fm_chunks[0].metadata["source"] == "https://example.com"

    def test_handles_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            f.flush()
            path = Path(f.name)

        chunks = chunk_markdown(path)
        path.unlink()

        assert chunks == []

    def test_handles_missing_file(self) -> None:
        path = Path("/nonexistent/file.md")
        chunks = chunk_markdown(path)
        assert chunks == []


class TestExtractCodeBlocks:
    """Tests for extract_code_blocks function."""

    def test_finds_code_blocks(self) -> None:
        content = """Some text

```python
def hello():
    pass
```

More text

```bash
echo "hi"
```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 2
        assert blocks[0][2] == "python"
        assert blocks[1][2] == "bash"

    def test_empty_content(self) -> None:
        blocks = extract_code_blocks("")
        assert blocks == []

    def test_no_code_blocks(self) -> None:
        blocks = extract_code_blocks("Just plain text.")
        assert blocks == []


class TestDocSchema:
    """Tests for document schema."""

    def test_schema_version(self) -> None:
        assert DOC_SCHEMA_VERSION == 1

    def test_schema_includes_dimensions(self) -> None:
        sql = get_doc_schema_sql(768)
        assert "FLOAT[768]" in sql
        assert "documents" in sql
        assert "doc_chunks" in sql

    def test_fts_triggers_defined(self) -> None:
        assert "doc_chunks_ai" in DOC_FTS_TRIGGERS
        assert "doc_chunks_ad" in DOC_FTS_TRIGGERS

    def test_init_creates_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_doc_database(str(db_path), 3)

            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]

            assert "documents" in table_names
            assert "doc_chunks" in table_names
            conn.close()


class TestDocIndexer:
    """Tests for DocIndexer class."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    @pytest.fixture
    def docs_dir(self) -> Path:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()

            (docs / "guide.md").write_text("""---
source: https://example.com/guide
fetched: 2024-01-15
---
# User Guide

## Installation

Run pip install.

## Configuration

Set up your config.
""")
            (docs / "api.md").write_text("""# API Reference

## Endpoints

GET /api/v1/users
""")
            yield docs

    @pytest.fixture
    def indexer(self, docs_dir: Path, mock_embedder: MagicMock) -> DocIndexer:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("personality.docs.indexer.DOCS_DIR", Path(tmpdir)),
        ):
            idx = DocIndexer(docs_dir, embedder=mock_embedder)
            yield idx
            idx.close()

    def test_db_path_is_in_docs_dir(self, indexer: DocIndexer) -> None:
        assert indexer.db_path.name == "index.db"

    def test_index_returns_stats(self, indexer: DocIndexer) -> None:
        stats = indexer.index()
        assert "files_indexed" in stats
        assert "chunks_created" in stats
        assert stats["files_indexed"] == 2

    def test_index_force_reindexes(self, indexer: DocIndexer) -> None:
        indexer.index()
        stats = indexer.index(force=True)
        assert stats["files_indexed"] == 2
        assert stats["files_skipped"] == 0

    def test_index_skips_unchanged(self, indexer: DocIndexer) -> None:
        indexer.index()
        stats = indexer.index()
        assert stats["files_skipped"] == 2
        assert stats["files_indexed"] == 0

    def test_status_returns_info(self, indexer: DocIndexer) -> None:
        indexer.index()
        status = indexer.status()
        assert status["document_count"] == 2
        assert status["chunk_count"] > 0

    def test_list_sources(self, indexer: DocIndexer) -> None:
        indexer.index()
        sources = indexer.list_sources()
        assert len(sources) == 2
        paths = [s["path"] for s in sources]
        assert "guide.md" in paths
        assert "api.md" in paths

    def test_search_returns_results(
        self, indexer: DocIndexer, mock_embedder: MagicMock
    ) -> None:
        indexer.index()
        results = indexer.search("installation")
        assert isinstance(results, list)

    def test_search_by_source(self, indexer: DocIndexer) -> None:
        indexer.index()
        results = indexer.search_by_source("example.com")
        assert len(results) >= 1
        assert all(r.source_url for r in results)

    def test_extracts_title_from_heading(self, indexer: DocIndexer) -> None:
        indexer.index()
        sources = indexer.list_sources()
        titles = [s["title"] for s in sources]
        assert "User Guide" in titles or "API Reference" in titles

    def test_extracts_source_from_frontmatter(self, indexer: DocIndexer) -> None:
        indexer.index()
        sources = indexer.list_sources()
        source_urls = [s["source_url"] for s in sources if s["source_url"]]
        assert "https://example.com/guide" in source_urls

    def test_close_releases_connection(self, indexer: DocIndexer) -> None:
        _ = indexer.conn
        assert indexer._conn is not None
        indexer.close()
        assert indexer._conn is None


class TestDocSearchResult:
    """Tests for DocSearchResult dataclass."""

    def test_creation(self) -> None:
        result = DocSearchResult(
            file_path="guide.md",
            title="User Guide",
            heading="Installation",
            content="Run pip install.",
            source_url="https://example.com",
            score=0.95,
        )
        assert result.file_path == "guide.md"
        assert result.score == 0.95

    def test_optional_fields(self) -> None:
        result = DocSearchResult(
            file_path="local.md",
            title=None,
            heading=None,
            content="Content",
            source_url=None,
            score=0.5,
        )
        assert result.title is None
        assert result.source_url is None


class TestGetDocIndexer:
    """Tests for get_doc_indexer function."""

    def test_default_path(self) -> None:
        indexer = get_doc_indexer()
        expected = Path.home() / "Projects" / "docs"
        assert indexer.docs_path == expected.resolve()

    def test_custom_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = get_doc_indexer(Path(tmpdir))
            assert indexer.docs_path == Path(tmpdir).resolve()


class TestDocIndexerEdgeCases:
    """Additional edge case tests for DocIndexer."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    def test_discover_finds_markdown_files(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir)
            (docs / "file.md").write_text("# Test")
            (docs / "file.markdown").write_text("# Test")
            (docs / "file.txt").write_text("Not markdown")
            (docs / "subdir").mkdir()
            (docs / "subdir" / "nested.md").write_text("# Nested")

            indexer = DocIndexer(docs, embedder=mock_embedder)
            files = indexer._discover_files()
            indexer.close()

            extensions = [f.suffix for f in files]
            assert ".md" in extensions
            assert ".txt" not in extensions

    def test_compute_hash_changes(self, mock_embedder: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir)
            test_file = docs / "test.md"
            test_file.write_text("# Original")

            indexer = DocIndexer(docs, embedder=mock_embedder)
            hash1 = indexer._compute_hash(test_file)

            test_file.write_text("# Changed")
            hash2 = indexer._compute_hash(test_file)

            indexer.close()

            assert hash1 != hash2

    def test_is_current_false_when_not_indexed(self, mock_embedder: MagicMock) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as db_tmpdir,
            patch("personality.docs.indexer.DOCS_DIR", Path(db_tmpdir)),
        ):
            docs = Path(tmpdir)
            indexer = DocIndexer(docs, embedder=mock_embedder)
            _ = indexer.conn

            assert not indexer._is_current("nonexistent.md", "abc123")
            indexer.close()

    def test_search_empty_index(self, mock_embedder: MagicMock) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as db_tmpdir,
            patch("personality.docs.indexer.DOCS_DIR", Path(db_tmpdir)),
        ):
            docs = Path(tmpdir)
            indexer = DocIndexer(docs, embedder=mock_embedder)
            _ = indexer.conn

            results = indexer.search("anything")
            assert results == []
            indexer.close()

    def test_search_by_source_empty(self, mock_embedder: MagicMock) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as db_tmpdir,
            patch("personality.docs.indexer.DOCS_DIR", Path(db_tmpdir)),
        ):
            docs = Path(tmpdir)
            indexer = DocIndexer(docs, embedder=mock_embedder)
            _ = indexer.conn

            results = indexer.search_by_source("nonexistent.com")
            assert results == []
            indexer.close()
