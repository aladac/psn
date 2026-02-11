"""Memory store with hybrid vector and full-text search."""

import logging
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path

from personality.memory.embedder import Embedder, get_embedder
from personality.memory.schema import init_database

logger = logging.getLogger(__name__)

DEFAULT_K = 5
DEFAULT_THRESHOLD = 0.7
CONSOLIDATE_THRESHOLD = 0.92


@dataclass
class Memory:
    """A memory entry."""

    id: int
    subject: str
    content: str
    source: str
    created_at: str
    accessed_at: str
    access_count: int
    score: float = 0.0


def serialize_f32(vec: list[float]) -> bytes:
    """Serialize float vector to bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


def escape_fts_query(query: str) -> str:
    """Escape query for FTS5 MATCH to prevent syntax errors."""
    # Wrap in quotes to treat as phrase, escape internal quotes
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


class MemoryStore:
    """Hybrid memory store with vector and full-text search."""

    def __init__(
        self,
        db_path: Path,
        embedder: Embedder | None = None,
    ):
        self.db_path = db_path
        self.embedder = embedder or get_embedder()
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = init_database(self.db_path, self.embedder.dimensions)
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def remember(
        self,
        subject: str,
        content: str,
        source: str = "manual",
    ) -> int:
        """Store a memory with embedding."""
        cursor = self.conn.execute(
            "INSERT INTO memories (subject, content, source) VALUES (?, ?, ?)",
            (subject, content, source),
        )
        memory_id = cursor.lastrowid

        embedding = self.embedder.embed(f"{subject}: {content}")
        self.conn.execute(
            "INSERT INTO memories_vec (id, embedding) VALUES (?, ?)",
            (memory_id, serialize_f32(embedding)),
        )
        self.conn.commit()
        logger.info("Stored memory %d: %s", memory_id, subject)
        return memory_id

    def recall(
        self,
        query: str,
        k: int = DEFAULT_K,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> list[Memory]:
        """Retrieve memories using hybrid search."""
        # Handle special "list all" queries
        if query.strip() in ("*", "all", ""):
            return self.list_all()[:k]

        query_embedding = self.embedder.embed(query)

        # Vector search with cosine similarity
        vec_results = self.conn.execute(
            """
            SELECT id, 1 - distance AS score
            FROM memories_vec
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (serialize_f32(query_embedding), k * 2),
        ).fetchall()

        # FTS search (escape query to handle special characters)
        fts_query = escape_fts_query(query)
        fts_results = self.conn.execute(
            """
            SELECT rowid, bm25(memories_fts) AS score
            FROM memories_fts
            WHERE memories_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, k * 2),
        ).fetchall()

        # Combine scores (RRF - Reciprocal Rank Fusion)
        scores: dict[int, float] = {}
        for rank, (mem_id, vec_score) in enumerate(vec_results):
            scores[mem_id] = scores.get(mem_id, 0) + 1 / (rank + 60)
            if vec_score >= threshold:
                scores[mem_id] += vec_score * 0.5

        for rank, (mem_id, _) in enumerate(fts_results):
            scores[mem_id] = scores.get(mem_id, 0) + 1 / (rank + 60)

        # Fetch full memories
        top_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:k]
        if not top_ids:
            return []

        memories = []
        for mem_id in top_ids:
            row = self.conn.execute(
                """
                SELECT id, subject, content, source, created_at, accessed_at, access_count
                FROM memories WHERE id = ?
                """,
                (mem_id,),
            ).fetchone()
            if row:
                self.conn.execute(
                    "UPDATE memories SET accessed_at = datetime('now'), access_count = access_count + 1 WHERE id = ?",
                    (mem_id,),
                )
                memories.append(Memory(*row, score=scores[mem_id]))

        self.conn.commit()
        return memories

    def forget(self, memory_id: int) -> bool:
        """Delete a memory by ID."""
        cursor = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cursor.rowcount > 0:
            self.conn.execute("DELETE FROM memories_vec WHERE id = ?", (memory_id,))
            self.conn.commit()
            logger.info("Forgot memory %d", memory_id)
            return True
        return False

    def consolidate(self, threshold: float = CONSOLIDATE_THRESHOLD) -> int:
        """Merge similar memories. Returns count of merged memories."""
        all_memories = self.list_all()
        if len(all_memories) < 2:
            return 0

        merged_count = 0
        to_delete = set()

        for i, mem1 in enumerate(all_memories):
            if mem1.id in to_delete:
                continue
            for mem2 in all_memories[i + 1 :]:
                if mem2.id in to_delete:
                    continue
                if mem1.subject != mem2.subject:
                    continue

                emb1 = self.embedder.embed(f"{mem1.subject}: {mem1.content}")
                emb2 = self.embedder.embed(f"{mem2.subject}: {mem2.content}")
                similarity = self._cosine_similarity(emb1, emb2)

                if similarity >= threshold:
                    combined = f"{mem1.content}\n{mem2.content}"
                    self.conn.execute(
                        "UPDATE memories SET content = ? WHERE id = ?",
                        (combined, mem1.id),
                    )
                    to_delete.add(mem2.id)
                    merged_count += 1
                    logger.info("Merged memory %d into %d", mem2.id, mem1.id)

        for mem_id in to_delete:
            self.forget(mem_id)

        return merged_count

    def list_all(self) -> list[Memory]:
        """Get all memories."""
        rows = self.conn.execute(
            """
            SELECT id, subject, content, source, created_at, accessed_at, access_count
            FROM memories ORDER BY accessed_at DESC
            """
        ).fetchall()
        return [Memory(*row) for row in rows]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
