"""Document indexer for markdown files."""

from personality.docs.chunker import DocChunk, chunk_markdown, parse_frontmatter
from personality.docs.indexer import DocIndexer, DocSearchResult, get_doc_indexer

__all__ = [
    "DocChunk",
    "DocIndexer",
    "DocSearchResult",
    "chunk_markdown",
    "get_doc_indexer",
    "parse_frontmatter",
]
