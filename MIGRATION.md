# Migration Plan: Local Vector Memory System

> **Objective:** Fully self-contained memory system using sqlite-vec + Ollama embeddings

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Personality                          │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Ollama    │  │  sqlite-vec │  │   Piper TTS     │  │
│  │  (embed)    │  │  (storage)  │  │   (voice)       │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │          │
│         └────────┬───────┘                   │          │
│                  ▼                           │          │
│         ┌───────────────┐                    │          │
│         │  Memory Store │                    │          │
│         │   (hybrid)    │                    │          │
│         └───────────────┘                    │          │
├─────────────────────────────────────────────────────────┤
│                    MCP Server                           │
│  Tools: speak, remember, recall, forget                 │
└─────────────────────────────────────────────────────────┘
```

**Zero external dependencies.** Everything runs locally.

---

## Phase 1: Ollama Embedding Integration

### Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "ollama>=0.4.0",
    "sqlite-vec>=0.1.0",
]
```

### Embedding Models (Recommended)

| Model | Dimensions | Size | Speed | Quality |
|-------|------------|------|-------|---------|
| `nomic-embed-text` | 768 | 274MB | Fast | High |
| `mxbai-embed-large` | 1024 | 670MB | Medium | Higher |
| `all-minilm` | 384 | 46MB | Fastest | Good |
| `snowflake-arctic-embed` | 1024 | 670MB | Medium | Highest |

**Recommendation:** `nomic-embed-text` for balance of quality and speed.

### Embedder Module

```python
# src/personality/memory/embedder.py
"""Local embedding via Ollama."""

import ollama
from functools import lru_cache

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
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = ollama.embed(model=self.model, input=text)
        return response["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = ollama.embed(model=self.model, input=texts)
        return response["embeddings"]

    def ensure_model(self) -> bool:
        """Pull model if not present."""
        try:
            ollama.show(self.model)
            return True
        except ollama.ResponseError:
            ollama.pull(self.model)
            return True


@lru_cache(maxsize=1)
def get_embedder(model: str = DEFAULT_MODEL) -> Embedder:
    """Get cached embedder instance."""
    return Embedder(model)
```

---

## Phase 2: sqlite-vec Memory Store

### Database Schema

```python
# src/personality/memory/schema.py
"""Database schema for vector memory."""

SCHEMA = """
-- Metadata table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    access_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    accessed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Vector index (dimensions set at runtime)
CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding float[{dimensions}]
);

-- Full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    subject,
    content,
    content='memories',
    content_rowid='rowid',
    tokenize='porter'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, subject, content)
    VALUES (NEW.rowid, NEW.subject, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, subject, content)
    VALUES ('delete', OLD.rowid, OLD.subject, OLD.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, subject, content)
    VALUES ('delete', OLD.rowid, OLD.subject, OLD.content);
    INSERT INTO memories_fts(rowid, subject, content)
    VALUES (NEW.rowid, NEW.subject, NEW.content);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_memories_subject ON memories(subject);
CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(accessed_at);
"""
```

### Memory Store Implementation

```python
# src/personality/memory/store.py
"""Vector memory store using sqlite-vec."""

import sqlite3
import sqlite_vec
import struct
import uuid
from dataclasses import dataclass
from pathlib import Path

from .embedder import Embedder, get_embedder
from .schema import SCHEMA


def serialize_f32(vector: list[float]) -> bytes:
    """Serialize float vector to binary format."""
    return struct.pack(f"{len(vector)}f", *vector)


@dataclass
class Memory:
    """A single memory entry."""

    id: str
    subject: str
    content: str
    source: str | None = None
    distance: float | None = None


class MemoryStore:
    """Hybrid vector + full-text memory storage."""

    def __init__(
        self,
        db_path: Path | str = ":memory:",
        embedder: Embedder | None = None,
    ):
        self.db_path = Path(db_path) if db_path != ":memory:" else db_path
        self.embedder = embedder or get_embedder()
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        schema = SCHEMA.format(dimensions=self.embedder.dimensions)
        self.conn.executescript(schema)
        self.conn.commit()

    def remember(
        self,
        subject: str,
        content: str,
        source: str | None = None,
    ) -> str:
        """Store a new memory with embedding."""
        memory_id = str(uuid.uuid4())
        embedding = self.embedder.embed(f"{subject}: {content}")

        with self.conn:
            # Insert metadata
            self.conn.execute(
                """
                INSERT INTO memories (id, subject, content, source)
                VALUES (?, ?, ?, ?)
                """,
                [memory_id, subject, content, source],
            )
            # Insert vector
            self.conn.execute(
                """
                INSERT INTO memories_vec (id, embedding)
                VALUES (?, ?)
                """,
                [memory_id, serialize_f32(embedding)],
            )

        return memory_id

    def recall(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.8,
    ) -> list[Memory]:
        """Hybrid search: vector similarity + full-text."""
        query_embedding = self.embedder.embed(query)

        # Vector search
        vec_results = self.conn.execute(
            """
            SELECT id, distance
            FROM memories_vec
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            [serialize_f32(query_embedding), k * 2],
        ).fetchall()

        # Full-text search
        fts_results = self.conn.execute(
            """
            SELECT m.id, bm25(memories_fts) as rank
            FROM memories_fts
            JOIN memories m ON memories_fts.rowid = m.rowid
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            [query, k * 2],
        ).fetchall()

        # Combine and deduplicate
        seen = set()
        combined = []

        for id_, distance in vec_results:
            if id_ not in seen and distance < threshold:
                seen.add(id_)
                combined.append((id_, distance))

        for id_, rank in fts_results:
            if id_ not in seen:
                seen.add(id_)
                # Convert BM25 rank to pseudo-distance
                combined.append((id_, 0.5))

        # Sort by distance and limit
        combined.sort(key=lambda x: x[1])
        top_ids = [id_ for id_, _ in combined[:k]]

        if not top_ids:
            return []

        # Fetch full memory data
        placeholders = ",".join("?" * len(top_ids))
        rows = self.conn.execute(
            f"""
            SELECT id, subject, content, source
            FROM memories
            WHERE id IN ({placeholders})
            """,
            top_ids,
        ).fetchall()

        # Preserve ranking order
        id_to_row = {row[0]: row for row in rows}
        id_to_dist = {id_: dist for id_, dist in combined[:k]}

        return [
            Memory(
                id=row[0],
                subject=row[1],
                content=row[2],
                source=row[3],
                distance=id_to_dist.get(row[0]),
            )
            for id_ in top_ids
            if (row := id_to_row.get(id_))
        ]

    def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM memories WHERE id = ?",
                [memory_id],
            )
            if cursor.rowcount > 0:
                self.conn.execute(
                    "DELETE FROM memories_vec WHERE id = ?",
                    [memory_id],
                )
                return True
        return False

    def consolidate(self, similarity_threshold: float = 0.85) -> int:
        """Merge similar memories. Returns count of merged."""
        # Get all memories with embeddings
        rows = self.conn.execute(
            """
            SELECT m.id, m.subject, m.content, v.embedding
            FROM memories m
            JOIN memories_vec v ON m.id = v.id
            ORDER BY m.created_at
            """,
        ).fetchall()

        merged = 0
        to_delete = set()

        for i, (id1, subj1, cont1, emb1) in enumerate(rows):
            if id1 in to_delete:
                continue

            for id2, subj2, cont2, emb2 in rows[i + 1 :]:
                if id2 in to_delete:
                    continue

                # Check similarity via vec_distance_cosine
                distance = self.conn.execute(
                    "SELECT vec_distance_cosine(?, ?)",
                    [emb1, emb2],
                ).fetchone()[0]

                similarity = 1 - distance
                if similarity > similarity_threshold:
                    # Keep the first, delete the second
                    to_delete.add(id2)
                    merged += 1

        for memory_id in to_delete:
            self.forget(memory_id)

        return merged

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
```

---

## Phase 3: MCP Integration

### New Memory Tools

```python
# src/personality/mcp/tools.py (additions)

from personality.memory.store import MemoryStore

# Add to AppContext
@dataclass
class AppContext:
    speak: Speak
    cart: Cart
    memory: MemoryStore  # NEW


@mcp.tool()
def remember(
    subject: str,
    content: str,
    ctx: Context,
) -> str:
    """Store a memory for later recall."""
    app: AppContext = ctx.request_context.lifespan_context
    memory_id = app.memory.remember(subject, content)
    return f"Memory stored: {memory_id}"


@mcp.tool()
def recall(
    query: str,
    limit: int = 5,
    ctx: Context,
) -> list[dict]:
    """Recall memories relevant to a query."""
    app: AppContext = ctx.request_context.lifespan_context
    memories = app.memory.recall(query, k=limit)
    return [
        {
            "subject": m.subject,
            "content": m.content,
            "relevance": 1 - (m.distance or 0),
        }
        for m in memories
    ]


@mcp.tool()
def forget(
    memory_id: str,
    ctx: Context,
) -> str:
    """Delete a specific memory."""
    app: AppContext = ctx.request_context.lifespan_context
    if app.memory.forget(memory_id):
        return f"Memory {memory_id} deleted"
    return f"Memory {memory_id} not found"
```

---

## Phase 4: Cart Integration

### Updated Cart Format

```yaml
# ~/.config/personality/carts/bt7274.yml
preferences:
  identity:
    name: "BT-7274"
    tagline: "Protocol 3: Protect the Pilot"
  speak:
    voice: "bt7274"
  memory:
    model: "nomic-embed-text"      # Ollama model for embeddings
    db: "bt7274.db"                # Per-cart memory database
    consolidate_threshold: 0.85   # Similarity for deduplication

memories:
  - subject: "self.protocol.1"
    content: "Link to Pilot - establish clear understanding of requirements"
  - subject: "self.protocol.2"
    content: "Uphold the Mission - complete objectives with precision"
  - subject: "self.protocol.3"
    content: "Protect the Pilot - prevent harm to Pilot and their codebase"
```

### Database Location

```
~/.config/personality/
├── carts/
│   └── bt7274.yml
├── voices/
│   └── bt7274.onnx
└── memory/              # NEW
    └── bt7274.db        # Per-cart sqlite database
```

---

## Phase 5: CLI Commands

### New Commands

```bash
# Memory operations
psn remember "user.preference.language" "Pilot prefers Python"
psn recall "what language does the pilot prefer"
psn forget <memory-id>

# Maintenance
psn consolidate              # Merge similar memories
psn memories list            # List all memories
psn memories export cart.db  # Export to portable format
psn memories import cart.db  # Import from backup
```

---

## Implementation Checklist

- [ ] Add `ollama` and `sqlite-vec` to dependencies
- [ ] Create `src/personality/memory/` module
  - [ ] `embedder.py` - Ollama embedding wrapper
  - [ ] `schema.py` - Database schema
  - [ ] `store.py` - MemoryStore class
- [ ] Update `AppContext` with memory store
- [ ] Add MCP tools: `remember`, `recall`, `forget`
- [ ] Update cart schema for memory config
- [ ] Add CLI commands for memory management
- [ ] Write tests for memory operations
- [ ] Update CLAUDE.md documentation

---

## Ollama Setup (One-Time)

```bash
# Install Ollama (macOS)
brew install ollama

# Start server
ollama serve

# Pull embedding model
ollama pull nomic-embed-text

# Verify
ollama list
```

---

## Testing

```python
# tests/test_memory.py
import pytest
from personality.memory.store import MemoryStore
from personality.memory.embedder import Embedder


@pytest.fixture
def store():
    """In-memory store for testing."""
    return MemoryStore(":memory:")


def test_remember_and_recall(store):
    store.remember("user.name", "The Pilot is called Chi")
    results = store.recall("what is the pilot's name")
    assert len(results) > 0
    assert "Chi" in results[0].content


def test_forget(store):
    memory_id = store.remember("test", "temporary data")
    assert store.forget(memory_id)
    assert not store.forget(memory_id)  # Already deleted


def test_consolidate(store):
    store.remember("greeting", "Hello there")
    store.remember("greeting", "Hello there!")  # Nearly identical
    merged = store.consolidate(similarity_threshold=0.9)
    assert merged == 1
```

---

_Compiled: 2026-02-11_
_Status: Ready for implementation_
