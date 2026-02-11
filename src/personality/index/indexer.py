"""Project indexer with semantic search."""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from personality.config import CONFIG_DIR
from personality.index.chunker import Chunk, chunk_file
from personality.index.schema import init_index_database
from personality.memory import Embedder, get_embedder
from personality.memory.store import serialize_f32

logger = logging.getLogger(__name__)

INDEX_DIR = CONFIG_DIR / "index"
REGISTRY_FILE = INDEX_DIR / "registry.json"

IGNORE_PATTERNS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".egg-info",
    "target",
}

CODE_EXTENSIONS = {".py", ".rb", ".rs", ".js", ".ts", ".tsx", ".jsx"}


@dataclass
class SearchResult:
    """A search result from the index."""

    file_path: str
    chunk_type: str
    name: str | None
    content: str
    start_line: int
    end_line: int
    score: float


class ProjectIndexer:
    """Index a project for semantic code search."""

    def __init__(self, project_path: Path, embedder: Embedder | None = None):
        self.project_path = project_path.resolve()
        self.embedder = embedder or get_embedder()
        self._conn: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        """Get the database path for this project."""
        project_hash = hashlib.md5(str(self.project_path).encode()).hexdigest()[:12]
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        return INDEX_DIR / f"{project_hash}.db"

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = init_index_database(str(self.db_path), self.embedder.dimensions)
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def index(self, force: bool = False) -> dict:
        """Index the project. Returns stats."""
        files_indexed = 0
        chunks_created = 0
        files_skipped = 0

        for file_path in self._discover_files():
            file_hash = self._compute_hash(file_path)
            relative_path = str(file_path.relative_to(self.project_path))

            if not force and self._is_current(relative_path, file_hash):
                files_skipped += 1
                continue

            self._remove_file(relative_path)
            chunks = chunk_file(file_path)

            if not chunks:
                continue

            file_id = self._add_file(relative_path, file_hash)
            self._add_chunks(file_id, chunks)

            files_indexed += 1
            chunks_created += len(chunks)

        self.conn.commit()
        self._update_registry()

        return {
            "files_indexed": files_indexed,
            "chunks_created": chunks_created,
            "files_skipped": files_skipped,
        }

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """Search the index for relevant chunks."""
        query_embedding = self.embedder.embed(query)

        results = self.conn.execute(
            """
            SELECT c.id, f.path, c.chunk_type, c.name, c.content,
                   c.start_line, c.end_line, 1 - v.distance AS score
            FROM chunks_vec v
            JOIN chunks c ON c.id = v.id
            JOIN files f ON f.id = c.file_id
            WHERE v.embedding MATCH ?
                AND k = ?
            ORDER BY v.distance
            """,
            (serialize_f32(query_embedding), k),
        ).fetchall()

        return [
            SearchResult(
                file_path=row[1],
                chunk_type=row[2],
                name=row[3],
                content=row[4],
                start_line=row[5],
                end_line=row[6],
                score=row[7],
            )
            for row in results
        ]

    def get_summary(self) -> str | None:
        """Get the project summary."""
        row = self.conn.execute("SELECT content FROM summary WHERE id = 1").fetchone()
        return row[0] if row else None

    def set_summary(self, content: str) -> None:
        """Set the project summary."""
        self.conn.execute(
            "INSERT OR REPLACE INTO summary (id, content) VALUES (1, ?)",
            (content,),
        )
        self.conn.commit()

    def status(self) -> dict:
        """Get index status."""
        file_count = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        chunk_count = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        has_summary = self.get_summary() is not None

        return {
            "project_path": str(self.project_path),
            "db_path": str(self.db_path),
            "file_count": file_count,
            "chunk_count": chunk_count,
            "has_summary": has_summary,
        }

    def _discover_files(self) -> list[Path]:
        """Discover indexable files in the project."""
        files = []

        for file_path in self.project_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in CODE_EXTENSIONS:
                continue
            if any(part in IGNORE_PATTERNS for part in file_path.parts):
                continue
            if self._is_gitignored(file_path):
                continue
            files.append(file_path)

        return files

    def _is_gitignored(self, path: Path) -> bool:
        """Check if a path is gitignored."""
        gitignore = self.project_path / ".gitignore"
        if not gitignore.exists():
            return False

        relative = path.relative_to(self.project_path)
        patterns = gitignore.read_text().splitlines()

        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith("#"):
                continue
            if pattern.rstrip("/") in str(relative):
                return True

        return False

    def _compute_hash(self, path: Path) -> str:
        """Compute file content hash."""
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _is_current(self, relative_path: str, file_hash: str) -> bool:
        """Check if file is already indexed with same hash."""
        row = self.conn.execute("SELECT hash FROM files WHERE path = ?", (relative_path,)).fetchone()
        return row is not None and row[0] == file_hash

    def _remove_file(self, relative_path: str) -> None:
        """Remove a file from the index."""
        self.conn.execute("DELETE FROM files WHERE path = ?", (relative_path,))

    def _add_file(self, relative_path: str, file_hash: str) -> int:
        """Add a file to the index, return file_id."""
        cursor = self.conn.execute(
            "INSERT INTO files (path, hash) VALUES (?, ?)",
            (relative_path, file_hash),
        )
        return cursor.lastrowid

    def _add_chunks(self, file_id: int, chunks: list[Chunk]) -> None:
        """Add chunks with embeddings."""
        for chunk in chunks:
            cursor = self.conn.execute(
                """
                INSERT INTO chunks (file_id, chunk_type, name, content, start_line, end_line)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_id, chunk.chunk_type, chunk.name, chunk.content, chunk.start_line, chunk.end_line),
            )
            chunk_id = cursor.lastrowid

            embedding = self.embedder.embed(f"{chunk.name or ''}: {chunk.content[:500]}")
            self.conn.execute(
                "INSERT INTO chunks_vec (id, embedding) VALUES (?, ?)",
                (chunk_id, serialize_f32(embedding)),
            )

    def _update_registry(self) -> None:
        """Update the project registry."""
        import json

        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)

        registry = {}
        if REGISTRY_FILE.exists():
            registry = json.loads(REGISTRY_FILE.read_text())

        registry[str(self.project_path)] = str(self.db_path)
        REGISTRY_FILE.write_text(json.dumps(registry, indent=2))


def get_indexer(project_path: Path | None = None) -> ProjectIndexer:
    """Get an indexer for a project path (default: cwd)."""
    if project_path is None:
        project_path = Path.cwd()
    return ProjectIndexer(project_path)


def list_indexed_projects() -> dict[str, str]:
    """List all indexed projects from registry."""
    import json

    if not REGISTRY_FILE.exists():
        return {}
    return json.loads(REGISTRY_FILE.read_text())
