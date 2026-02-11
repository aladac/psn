"""Local embedding via Ollama."""

import logging
from functools import lru_cache

import ollama

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "nomic-embed-text"


class Embedder:
    """Generate embeddings using local Ollama models."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._dimensions: int | None = None

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions (cached after first call)."""
        if self._dimensions is None:
            test = self.embed("test")
            self._dimensions = len(test)
            logger.debug("Embedding dimensions: %d", self._dimensions)
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = ollama.embed(model=self.model, input=text)
        return response["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        response = ollama.embed(model=self.model, input=texts)
        return response["embeddings"]

    def ensure_model(self) -> bool:
        """Pull model if not present. Returns True if ready."""
        try:
            ollama.show(self.model)
            logger.debug("Model %s already available", self.model)
            return True
        except ollama.ResponseError:
            logger.info("Pulling model %s...", self.model)
            ollama.pull(self.model)
            return True


@lru_cache(maxsize=1)
def get_embedder(model: str = DEFAULT_MODEL) -> Embedder:
    """Get cached embedder instance."""
    return Embedder(model)
