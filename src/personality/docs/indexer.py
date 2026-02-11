"""Document indexer with semantic search."""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from personality.config import CONFIG_DIR
from personality.docs.chunker import DocChunk, chunk_markdown
from personality.docs.schema import init_doc_database
from personality.memory import Embedder, get_embedder
from personality.memory.store import escape_fts_query, serialize_f32

logger = logging.getLogger(__name__)

DOCS_DIR = CONFIG_DIR / "docs"
DEFAULT_K = 5


@dataclass
class DocSearchResult:
    """A search result from the document index."""

    file_path: str
    title: str | None
    heading: str | None
    content: str
    source_url: str | None
    score: float


class DocIndexer:
    """Index markdown documents for semantic search."""

    def __init__(self, docs_path: Path, embedder: Embedder | None = None):
        self.docs_path = docs_path.resolve()
        self.embedder = embedder or get_embedder()
        self._conn: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        """Get the database path for the docs index."""
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        return DOCS_DIR / "index.db"

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = init_doc_database(str(self.db_path), self.embedder.dimensions)
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def index(self, force: bool = False) -> dict:
        """Index all markdown files in the docs path."""
        files_indexed = 0
        chunks_created = 0
        files_skipped = 0

        for file_path in self._discover_files():
            file_hash = self._compute_hash(file_path)
            relative_path = str(file_path.relative_to(self.docs_path))

            if not force and self._is_current(relative_path, file_hash):
                files_skipped += 1
                continue

            self._remove_document(relative_path)
            chunks = chunk_markdown(file_path)

            if not chunks:
                continue

            title = self._extract_title(chunks, file_path)
            source_url, fetched_at = self._extract_source(chunks)

            doc_id = self._add_document(relative_path, file_hash, title, source_url, fetched_at)
            self._add_chunks(doc_id, chunks)

            files_indexed += 1
            chunks_created += len(chunks)

        self.conn.commit()

        return {
            "files_indexed": files_indexed,
            "chunks_created": chunks_created,
            "files_skipped": files_skipped,
        }

    def search(self, query: str, k: int = DEFAULT_K) -> list[DocSearchResult]:
        """Hybrid vector + FTS search with RRF ranking."""
        query_embedding = self.embedder.embed(query)

        # Vector search
        vec_results = self.conn.execute(
            """
            SELECT id, 1 - distance AS score
            FROM doc_chunks_vec
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (serialize_f32(query_embedding), k * 2),
        ).fetchall()

        # FTS search
        fts_query = escape_fts_query(query)
        fts_results = self.conn.execute(
            """
            SELECT rowid, bm25(doc_chunks_fts) AS score
            FROM doc_chunks_fts
            WHERE doc_chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, k * 2),
        ).fetchall()

        # Combine with RRF
        scores: dict[int, float] = {}
        for rank, (chunk_id, vec_score) in enumerate(vec_results):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (rank + 60)
            if vec_score >= 0.7:
                scores[chunk_id] += vec_score * 0.5

        for rank, (chunk_id, _) in enumerate(fts_results):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (rank + 60)

        top_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:k]
        return self._fetch_results(top_ids, scores)

    def search_by_source(self, url_pattern: str, k: int = DEFAULT_K) -> list[DocSearchResult]:
        """Find documents from specific source URLs."""
        rows = self.conn.execute(
            """
            SELECT d.path, d.title, c.heading, c.content, d.source_url
            FROM documents d
            JOIN doc_chunks c ON c.document_id = d.id
            WHERE d.source_url LIKE ?
            ORDER BY d.indexed_at DESC
            LIMIT ?
            """,
            (f"%{url_pattern}%", k),
        ).fetchall()

        return [
            DocSearchResult(
                file_path=row[0],
                title=row[1],
                heading=row[2],
                content=row[3],
                source_url=row[4],
                score=1.0,
            )
            for row in rows
        ]

    def status(self) -> dict:
        """Get index status."""
        doc_count = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunk_count = self.conn.execute("SELECT COUNT(*) FROM doc_chunks").fetchone()[0]

        return {
            "docs_path": str(self.docs_path),
            "db_path": str(self.db_path),
            "document_count": doc_count,
            "chunk_count": chunk_count,
        }

    def list_sources(self) -> list[dict]:
        """List all indexed documents with metadata."""
        rows = self.conn.execute(
            """
            SELECT path, title, source_url, fetched_at, indexed_at
            FROM documents
            ORDER BY indexed_at DESC
            """
        ).fetchall()

        return [
            {
                "path": row[0],
                "title": row[1],
                "source_url": row[2],
                "fetched_at": row[3],
                "indexed_at": row[4],
            }
            for row in rows
        ]

    def _discover_files(self) -> list[Path]:
        """Discover markdown files in the docs path."""
        files = []
        for pattern in ("**/*.md", "**/*.markdown"):
            for file_path in self.docs_path.glob(pattern):
                if file_path.is_file():
                    files.append(file_path)
        return files

    def _compute_hash(self, path: Path) -> str:
        """Compute file content hash."""
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _is_current(self, relative_path: str, file_hash: str) -> bool:
        """Check if file is already indexed with same hash."""
        row = self.conn.execute(
            "SELECT file_hash FROM documents WHERE path = ?",
            (relative_path,),
        ).fetchone()
        return row is not None and row[0] == file_hash

    def _remove_document(self, relative_path: str) -> None:
        """Remove a document from the index."""
        self.conn.execute("DELETE FROM documents WHERE path = ?", (relative_path,))

    def _add_document(
        self,
        relative_path: str,
        file_hash: str,
        title: str | None,
        source_url: str | None,
        fetched_at: str | None,
    ) -> int:
        """Add a document to the index."""
        cursor = self.conn.execute(
            """
            INSERT INTO documents (path, file_hash, title, source_url, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (relative_path, file_hash, title, source_url, fetched_at),
        )
        return cursor.lastrowid

    def _add_chunks(self, doc_id: int, chunks: list[DocChunk]) -> None:
        """Add chunks with embeddings."""
        for chunk in chunks:
            cursor = self.conn.execute(
                """
                INSERT INTO doc_chunks (document_id, chunk_type, heading, content, start_line, end_line)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (doc_id, chunk.chunk_type, chunk.heading, chunk.content, chunk.start_line, chunk.end_line),
            )
            chunk_id = cursor.lastrowid

            # Create embedding from heading + content
            embed_text = f"{chunk.heading or ''}: {chunk.content[:500]}"
            embedding = self.embedder.embed(embed_text)
            self.conn.execute(
                "INSERT INTO doc_chunks_vec (id, embedding) VALUES (?, ?)",
                (chunk_id, serialize_f32(embedding)),
            )

    def _fetch_results(self, chunk_ids: list[int], scores: dict[int, float]) -> list[DocSearchResult]:
        """Fetch full results for chunk IDs."""
        results = []
        for chunk_id in chunk_ids:
            row = self.conn.execute(
                """
                SELECT d.path, d.title, c.heading, c.content, d.source_url
                FROM doc_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.id = ?
                """,
                (chunk_id,),
            ).fetchone()
            if row:
                results.append(
                    DocSearchResult(
                        file_path=row[0],
                        title=row[1],
                        heading=row[2],
                        content=row[3],
                        source_url=row[4],
                        score=scores[chunk_id],
                    )
                )
        return results

    def _extract_title(self, chunks: list[DocChunk], path: Path) -> str | None:
        """Extract title from first H1 heading or filename."""
        for chunk in chunks:
            if chunk.chunk_type == "section" and chunk.heading:
                return chunk.heading
        return path.stem.replace("-", " ").replace("_", " ").title()

    def _extract_source(self, chunks: list[DocChunk]) -> tuple[str | None, str | None]:
        """Extract source URL and fetch date from frontmatter."""
        for chunk in chunks:
            if chunk.chunk_type == "frontmatter":
                source = chunk.metadata.get("source")
                fetched = chunk.metadata.get("fetched")
                return source, str(fetched) if fetched else None
        return None, None


def get_doc_indexer(docs_path: Path | None = None) -> DocIndexer:
    """Get a doc indexer for a path (default: ~/Projects/docs)."""
    if docs_path is None:
        docs_path = Path.home() / "Projects" / "docs"
    return DocIndexer(docs_path)
