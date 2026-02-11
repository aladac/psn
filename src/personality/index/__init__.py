"""Project indexing module for semantic code search."""

from personality.index.chunker import Chunk, chunk_file, detect_language, sliding_window_chunks
from personality.index.indexer import (
    ProjectIndexer,
    SearchResult,
    get_indexer,
    list_indexed_projects,
)
from personality.index.schema import init_index_database

__all__ = [
    "Chunk",
    "ProjectIndexer",
    "SearchResult",
    "chunk_file",
    "detect_language",
    "get_indexer",
    "init_index_database",
    "list_indexed_projects",
    "sliding_window_chunks",
]
