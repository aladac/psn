"""Database schema for memory storage with vector and full-text search."""

import sqlite3
from pathlib import Path

import sqlite_vec

SCHEMA_VERSION = 1


def get_schema_sql(embedding_dims: int) -> str:
    """Generate schema SQL with correct embedding dimensions."""
    return f"""
-- Memory entries table
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now')),
    accessed_at TEXT DEFAULT (datetime('now')),
    access_count INTEGER DEFAULT 0
);

-- Vector storage (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(
    id INTEGER PRIMARY KEY,
    embedding FLOAT[{embedding_dims}]
);

-- Full-text search (FTS5 with porter stemmer)
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    subject,
    content,
    tokenize='porter'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_memories_subject ON memories(subject);
CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(accessed_at);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES ({SCHEMA_VERSION});
"""


FTS_SYNC_TRIGGERS = """
-- Sync triggers for FTS
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, subject, content)
    VALUES (NEW.id, NEW.subject, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    DELETE FROM memories_fts WHERE rowid = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    DELETE FROM memories_fts WHERE rowid = OLD.id;
    INSERT INTO memories_fts(rowid, subject, content)
    VALUES (NEW.id, NEW.subject, NEW.content);
END;
"""


def init_database(db_path: Path, embedding_dims: int) -> sqlite3.Connection:
    """Initialize database with schema and extensions."""
    conn = sqlite3.connect(str(db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.executescript(get_schema_sql(embedding_dims))
    conn.executescript(FTS_SYNC_TRIGGERS)
    conn.commit()

    return conn
