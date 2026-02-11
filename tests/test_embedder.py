"""Tests for personality.memory.embedder module."""

from unittest.mock import MagicMock, patch

from personality.memory.embedder import DEFAULT_MODEL, Embedder, get_embedder


class TestEmbedder:
    """Tests for Embedder class."""

    def test_init_with_default_model(self) -> None:
        embedder = Embedder()
        assert embedder.model == DEFAULT_MODEL

    def test_init_with_custom_model(self) -> None:
        embedder = Embedder(model="custom-model")
        assert embedder.model == "custom-model"

    @patch("personality.memory.embedder.ollama")
    def test_embed_single_text(self, mock_ollama: MagicMock) -> None:
        mock_ollama.embed.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        embedder = Embedder()
        result = embedder.embed("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_ollama.embed.assert_called_once_with(model=DEFAULT_MODEL, input="test text")

    @patch("personality.memory.embedder.ollama")
    def test_embed_batch(self, mock_ollama: MagicMock) -> None:
        mock_ollama.embed.return_value = {"embeddings": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]}

        embedder = Embedder()
        result = embedder.embed_batch(["text1", "text2", "text3"])

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_ollama.embed.assert_called_once_with(model=DEFAULT_MODEL, input=["text1", "text2", "text3"])

    def test_embed_batch_empty_list(self) -> None:
        embedder = Embedder()
        result = embedder.embed_batch([])
        assert result == []

    @patch("personality.memory.embedder.ollama")
    def test_dimensions_property(self, mock_ollama: MagicMock) -> None:
        mock_ollama.embed.return_value = {"embeddings": [[0.1, 0.2, 0.3, 0.4]]}

        embedder = Embedder()
        dims = embedder.dimensions

        assert dims == 4
        mock_ollama.embed.assert_called_once()

    @patch("personality.memory.embedder.ollama")
    def test_dimensions_cached(self, mock_ollama: MagicMock) -> None:
        mock_ollama.embed.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        embedder = Embedder()
        _ = embedder.dimensions
        _ = embedder.dimensions

        # Should only call embed once due to caching
        assert mock_ollama.embed.call_count == 1

    @patch("personality.memory.embedder.ollama")
    def test_ensure_model_already_exists(self, mock_ollama: MagicMock) -> None:
        mock_ollama.show.return_value = {"model": DEFAULT_MODEL}

        embedder = Embedder()
        result = embedder.ensure_model()

        assert result is True
        mock_ollama.show.assert_called_once_with(DEFAULT_MODEL)
        mock_ollama.pull.assert_not_called()

    @patch("personality.memory.embedder.ollama")
    def test_ensure_model_pulls_if_missing(self, mock_ollama: MagicMock) -> None:
        import ollama as ollama_module

        mock_ollama.ResponseError = ollama_module.ResponseError
        mock_ollama.show.side_effect = ollama_module.ResponseError("not found")

        embedder = Embedder()
        result = embedder.ensure_model()

        assert result is True
        mock_ollama.pull.assert_called_once_with(DEFAULT_MODEL)


class TestGetEmbedder:
    """Tests for get_embedder factory function."""

    def test_returns_embedder_instance(self) -> None:
        get_embedder.cache_clear()
        embedder = get_embedder()
        assert isinstance(embedder, Embedder)

    def test_returns_cached_instance(self) -> None:
        get_embedder.cache_clear()
        embedder1 = get_embedder()
        embedder2 = get_embedder()
        assert embedder1 is embedder2

    def test_accepts_custom_model(self) -> None:
        get_embedder.cache_clear()
        embedder = get_embedder("custom-model")
        assert embedder.model == "custom-model"
