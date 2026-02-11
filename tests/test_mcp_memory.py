"""Tests for MCP memory tools and resources."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personality.mcp.server import AppContext, _get_memory_db_path
from personality.mcp.tools import (
    DEFAULT_RECALL_LIMIT,
    _format_memories,
    consolidate,
    forget,
    recall,
    remember,
    stop_speaking,
)
from personality.memory import Memory, MemoryStore


class TestStopSpeaking:
    """Tests for stop_speaking tool."""

    @pytest.mark.asyncio
    @patch("personality.mcp.tools.Speak")
    async def test_stop_speaking_when_playing(self, mock_speak: MagicMock) -> None:
        mock_speak.stop.return_value = True
        result = await stop_speaking()
        assert result == "Stopped audio playback"

    @pytest.mark.asyncio
    @patch("personality.mcp.tools.Speak")
    async def test_stop_speaking_when_not_playing(self, mock_speak: MagicMock) -> None:
        mock_speak.stop.return_value = False
        result = await stop_speaking()
        assert result == "No audio was playing"


class TestMemoryTools:
    """Tests for memory MCP tools."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.dimensions = 3
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        return embedder

    @pytest.fixture
    def memory_store(self, mock_embedder: MagicMock) -> MemoryStore:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path, embedder=mock_embedder)
            yield store
            store.close()

    @pytest.fixture
    def app_context(self, memory_store: MemoryStore) -> AppContext:
        return AppContext(
            cart_name="test",
            cart_data=None,
            voice_dir="/tmp",
            memory=memory_store,
        )

    @pytest.fixture
    def mock_ctx(self, app_context: AppContext) -> MagicMock:
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_context
        return ctx

    @pytest.mark.asyncio
    async def test_remember_stores_memory(self, mock_ctx: MagicMock) -> None:
        result = await remember("test.subject", "test content", mock_ctx)
        assert "Remembered" in result
        assert "id=" in result

    @pytest.mark.asyncio
    async def test_remember_without_memory_store(self) -> None:
        ctx = MagicMock()
        ctx.request_context.lifespan_context = AppContext(
            cart_name="test", cart_data=None, voice_dir="/tmp", memory=None
        )
        result = await remember("test", "content", ctx)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_recall_returns_memories(self, mock_ctx: MagicMock, memory_store: MemoryStore) -> None:
        memory_store.remember("protocols", "Protocol 1: Link to Pilot")
        result = await recall("protocol", mock_ctx)
        assert "protocols" in result

    @pytest.mark.asyncio
    async def test_recall_empty_returns_message(self, mock_ctx: MagicMock) -> None:
        result = await recall("nonexistent query", mock_ctx)
        assert "No relevant memories" in result

    @pytest.mark.asyncio
    async def test_recall_with_limit(self, mock_ctx: MagicMock, memory_store: MemoryStore) -> None:
        for i in range(10):
            memory_store.remember(f"test{i}", f"content {i}")
        result = await recall("test", mock_ctx, limit=3)
        # Should have limited results
        assert result.count("**[") <= 3

    @pytest.mark.asyncio
    async def test_forget_removes_memory(self, mock_ctx: MagicMock, memory_store: MemoryStore) -> None:
        mem_id = memory_store.remember("test", "to delete")
        result = await forget(mem_id, mock_ctx)
        assert f"Forgot memory {mem_id}" in result

    @pytest.mark.asyncio
    async def test_forget_nonexistent(self, mock_ctx: MagicMock) -> None:
        result = await forget(999, mock_ctx)
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_consolidate_merges_similar(
        self, mock_ctx: MagicMock, mock_embedder: MagicMock, memory_store: MemoryStore
    ) -> None:
        mock_embedder.embed.return_value = [0.5, 0.5, 0.5]
        memory_store.remember("protocols", "Protocol 1")
        memory_store.remember("protocols", "Protocol 1 detail")
        result = await consolidate(mock_ctx, threshold=0.99)
        assert "Consolidated" in result


class TestFormatMemories:
    """Tests for _format_memories helper."""

    def test_format_single_memory(self) -> None:
        memories = [
            Memory(
                id=1,
                subject="test",
                content="content here",
                source="manual",
                created_at="2024-01-01",
                accessed_at="2024-01-01",
                access_count=0,
                score=0.85,
            )
        ]
        result = _format_memories(memories)
        assert "**[1] test**" in result
        assert "0.85" in result
        assert "content here" in result

    def test_format_truncates_long_content(self) -> None:
        long_content = "x" * 300
        memories = [
            Memory(
                id=1,
                subject="test",
                content=long_content,
                source="manual",
                created_at="2024-01-01",
                accessed_at="2024-01-01",
                access_count=0,
                score=0.5,
            )
        ]
        result = _format_memories(memories)
        assert "..." in result
        assert len(result) < len(long_content)


class TestGetMemoryDbPath:
    """Tests for _get_memory_db_path helper."""

    def test_returns_path_for_cart(self) -> None:
        path = _get_memory_db_path("bt7274")
        assert path.name == "bt7274.db"
        assert "memory" in str(path)


class TestConstants:
    """Tests for module constants."""

    def test_default_recall_limit(self) -> None:
        assert DEFAULT_RECALL_LIMIT == 5


class TestProjectTools:
    """Tests for project MCP tools."""

    @pytest.mark.asyncio
    async def test_project_search_returns_results(self) -> None:
        from personality.mcp.tools import project_search

        mock_indexer = MagicMock()
        mock_indexer.search.return_value = [
            MagicMock(
                file_path="test.py",
                chunk_type="function",
                name="test_func",
                content="def test(): pass",
                start_line=1,
                end_line=1,
                score=0.9,
            )
        ]

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = await project_search("test function")

        assert "test.py" in result
        mock_indexer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_search_no_results(self) -> None:
        from personality.mcp.tools import project_search

        mock_indexer = MagicMock()
        mock_indexer.search.return_value = []

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = await project_search("nonexistent")

        assert "No matching code" in result

    @pytest.mark.asyncio
    async def test_project_search_handles_error(self) -> None:
        from personality.mcp.tools import project_search

        with patch("personality.index.get_indexer", side_effect=Exception("Index not found")):
            result = await project_search("test")

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_project_summary(self) -> None:
        from personality.mcp.tools import project_summary

        mock_indexer = MagicMock()
        mock_indexer.get_summary.return_value = "Test project summary"
        mock_indexer.status.return_value = {
            "project_path": "/test/path",
            "file_count": 10,
            "chunk_count": 50,
        }

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = await project_summary()

        assert "Test project summary" in result
        assert "10" in result

    @pytest.mark.asyncio
    async def test_project_summary_no_summary(self) -> None:
        from personality.mcp.tools import project_summary

        mock_indexer = MagicMock()
        mock_indexer.get_summary.return_value = None
        mock_indexer.status.return_value = {
            "project_path": "/test/path",
            "file_count": 0,
            "chunk_count": 0,
        }

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = await project_summary()

        assert "No summary" in result
