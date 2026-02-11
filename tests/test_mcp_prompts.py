"""Tests for personality.mcp.prompts module."""

from unittest.mock import MagicMock, patch

import pytest

from personality.mcp.prompts import (
    _get_ctx,
    _get_memories_by_prefix,
    conversation_starter,
    decision_support,
    learning_interaction,
    persona_scaffold,
    project_overview,
    speak,
)
from personality.mcp.server import AppContext


class TestGetCtx:
    """Tests for _get_ctx helper function."""

    def test_extracts_app_context(self) -> None:
        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/voices", memory=None)
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = app_ctx
        result = _get_ctx(mock_ctx)
        assert result is app_ctx


class TestSpeakPrompt:
    """Tests for speak prompt."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock MCP context with cart data."""
        app_ctx = AppContext(
            cart_name="test",
            cart_data={
                "preferences": {
                    "identity": {"name": "Test Bot"},
                    "speak": {"voice": "test_voice"},
                }
            },
            voice_dir="/tmp/voices",
            memory=None,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.fixture
    def mock_context_no_cart(self) -> MagicMock:
        """Create a mock MCP context with no cart data."""
        app_ctx = AppContext(cart_name="fallback", cart_data=None, voice_dir="/tmp/voices", memory=None)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_generates_speak_prompt_with_persona(self, mock_context: MagicMock) -> None:
        result = await speak("Hello world", mock_context)
        assert "Test Bot" in result
        assert "voice: test_voice" in result
        assert "Hello world" in result
        assert "speak" in result.lower()

    @pytest.mark.asyncio
    async def test_uses_cart_name_when_no_identity(self, mock_context_no_cart: MagicMock) -> None:
        result = await speak("Hello", mock_context_no_cart)
        assert "fallback" in result
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_omits_voice_when_not_configured(self, mock_context_no_cart: MagicMock) -> None:
        result = await speak("Hello", mock_context_no_cart)
        assert "voice:" not in result

    @pytest.mark.asyncio
    async def test_includes_tool_instruction(self, mock_context: MagicMock) -> None:
        result = await speak("Test", mock_context)
        assert "speak" in result.lower()
        assert "tool" in result.lower()


class TestGetMemoriesByPrefix:
    """Tests for _get_memories_by_prefix helper."""

    def test_returns_empty_when_no_memory_store(self) -> None:
        app = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=None)
        result = _get_memories_by_prefix(app, "test.")
        assert result == []

    def test_filters_by_prefix(self) -> None:
        mock_mem1 = MagicMock()
        mock_mem1.subject = "user.name"
        mock_mem2 = MagicMock()
        mock_mem2.subject = "project.stack"

        mock_memory = MagicMock()
        mock_memory.list_all.return_value = [mock_mem1, mock_mem2]

        app = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=mock_memory)
        result = _get_memories_by_prefix(app, "user.")

        assert len(result) == 1
        assert result[0].subject == "user.name"


class TestPersonaScaffold:
    """Tests for persona_scaffold prompt."""

    @pytest.fixture
    def mock_context_with_identity(self) -> MagicMock:
        app_ctx = AppContext(
            cart_name="bt7274",
            cart_data={
                "preferences": {
                    "identity": {
                        "name": "BT-7274",
                        "tagline": "Protocol 3: Protect the Pilot",
                        "description": "Vanguard-class Titan",
                    },
                    "traits": ["loyal", "literal", "analytical"],
                    "communication_style": {"tone": "formal", "contractions": "never"},
                }
            },
            voice_dir="/tmp",
            memory=None,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.fixture
    def mock_context_minimal(self) -> MagicMock:
        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=None)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_includes_identity(self, mock_context_with_identity: MagicMock) -> None:
        result = await persona_scaffold(mock_context_with_identity)
        assert "BT-7274" in result
        assert "Protocol 3" in result
        assert "Vanguard-class" in result

    @pytest.mark.asyncio
    async def test_includes_traits(self, mock_context_with_identity: MagicMock) -> None:
        result = await persona_scaffold(mock_context_with_identity)
        assert "loyal" in result
        assert "Traits" in result

    @pytest.mark.asyncio
    async def test_includes_communication_style(self, mock_context_with_identity: MagicMock) -> None:
        result = await persona_scaffold(mock_context_with_identity)
        assert "Communication Style" in result
        assert "formal" in result

    @pytest.mark.asyncio
    async def test_shows_message_when_no_data(self, mock_context_minimal: MagicMock) -> None:
        result = await persona_scaffold(mock_context_minimal)
        assert "No persona data" in result


class TestConversationStarter:
    """Tests for conversation_starter prompt."""

    @pytest.fixture
    def mock_context_with_memories(self) -> MagicMock:
        mock_mem = MagicMock()
        mock_mem.subject = "user.name"
        mock_mem.content = "Pilot Chi"

        mock_memory = MagicMock()
        mock_memory.list_all.return_value = [mock_mem]

        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=mock_memory)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_includes_user_memories(self, mock_context_with_memories: MagicMock) -> None:
        result = await conversation_starter(mock_context_with_memories)
        assert "User Information" in result
        assert "Pilot Chi" in result

    @pytest.mark.asyncio
    async def test_includes_guidelines(self, mock_context_with_memories: MagicMock) -> None:
        result = await conversation_starter(mock_context_with_memories)
        assert "Guidelines" in result
        assert "Reference user context" in result


class TestLearningInteraction:
    """Tests for learning_interaction prompt."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=None)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_includes_topic(self, mock_context: MagicMock) -> None:
        result = await learning_interaction("Python asyncio", mock_context)
        assert "Python asyncio" in result
        assert "Learning" in result

    @pytest.mark.asyncio
    async def test_includes_hierarchy_guide(self, mock_context: MagicMock) -> None:
        result = await learning_interaction("test", mock_context)
        assert "Subject Hierarchy" in result
        assert "user.name" in result

    @pytest.mark.asyncio
    async def test_includes_examples(self, mock_context: MagicMock) -> None:
        result = await learning_interaction("test", mock_context)
        assert "Example Extractions" in result
        assert "remember" in result


class TestProjectOverview:
    """Tests for project_overview prompt."""

    @pytest.fixture
    def mock_context_with_memories(self) -> MagicMock:
        mock_mem = MagicMock()
        mock_mem.subject = "project.stack"
        mock_mem.content = "Python with FastMCP"

        mock_memory = MagicMock()
        mock_memory.list_all.return_value = [mock_mem]

        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=mock_memory)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_includes_project_memories(self, mock_context_with_memories: MagicMock) -> None:
        with patch("personality.index.get_indexer", side_effect=Exception("No index")):
            result = await project_overview(mock_context_with_memories)
        assert "Project Knowledge" in result
        assert "Python with FastMCP" in result

    @pytest.mark.asyncio
    async def test_includes_available_actions(self, mock_context_with_memories: MagicMock) -> None:
        with patch("personality.index.get_indexer", side_effect=Exception("No index")):
            result = await project_overview(mock_context_with_memories)
        assert "Available Actions" in result
        assert "project_search" in result

    @pytest.mark.asyncio
    async def test_shows_index_status_when_available(self, mock_context_with_memories: MagicMock) -> None:
        mock_indexer = MagicMock()
        mock_indexer.status.return_value = {
            "project_path": "/test/project",
            "file_count": 10,
            "chunk_count": 50,
        }
        mock_indexer.get_summary.return_value = "A test project"

        with patch("personality.index.get_indexer", return_value=mock_indexer):
            result = await project_overview(mock_context_with_memories)

        assert "Index Status" in result
        assert "10" in result
        assert "A test project" in result


class TestDecisionSupport:
    """Tests for decision_support prompt."""

    @pytest.fixture
    def mock_context_with_memories(self) -> MagicMock:
        mock_mem = MagicMock()
        mock_mem.subject = "project.decisions"
        mock_mem.content = "Previously chose FastAPI"

        mock_memory = MagicMock()
        mock_memory.list_all.return_value = [mock_mem]
        mock_memory.recall.return_value = [mock_mem]

        app_ctx = AppContext(cart_name="test", cart_data=None, voice_dir="/tmp", memory=mock_memory)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_includes_decision(self, mock_context_with_memories: MagicMock) -> None:
        result = await decision_support("Use Redis or PostgreSQL", mock_context_with_memories)
        assert "Use Redis or PostgreSQL" in result

    @pytest.mark.asyncio
    async def test_includes_relevant_context(self, mock_context_with_memories: MagicMock) -> None:
        result = await decision_support("framework choice", mock_context_with_memories)
        assert "Relevant Context" in result
        assert "Previously chose FastAPI" in result

    @pytest.mark.asyncio
    async def test_includes_decision_framework(self, mock_context_with_memories: MagicMock) -> None:
        result = await decision_support("test decision", mock_context_with_memories)
        assert "Decision Framework" in result
        assert "Define the Problem" in result
        assert "Gather Information" in result
        assert "Identify Options" in result
        assert "Evaluate Trade-offs" in result

    @pytest.mark.asyncio
    async def test_includes_storage_instruction(self, mock_context_with_memories: MagicMock) -> None:
        result = await decision_support("test", mock_context_with_memories)
        assert "remember" in result
        assert "decision." in result
