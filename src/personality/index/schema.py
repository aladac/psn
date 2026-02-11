"""Database schema for project index with vector and full-text search."""

import sqlite3

import sqlite_vec

INDEX_SCHEMA_VERSION = 1


def get_index_schema_sql(embedding_dims: int) -> str:
    """Generate index schema SQL with correct embedding dimensions."""
    return f"""
-- Indexed files for change detection
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    hash TEXT NOT NULL,
    indexed_at TEXT DEFAULT (datetime('now'))
);

-- Code chunks extracted from files
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    chunk_type TEXT NOT NULL,
    name TEXT,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    UNIQUE(file_id, chunk_type, name, start_line)
);

-- Vector storage for chunks (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
    id INTEGER PRIMARY KEY,
    embedding FLOAT[{embedding_dims}]
);

-- Full-text search for chunks (FTS5 with porter stemmer)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    name,
    content,
    tokenize='porter'
);

-- Project summary
CREATE TABLE IF NOT EXISTS summary (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    content TEXT,
    generated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);

-- Schema version
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES ({INDEX_SCHEMA_VERSION});
"""


INDEX_FTS_TRIGGERS = """
-- Sync triggers for FTS
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, name, content)
    VALUES (NEW.id, NEW.name, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    DELETE FROM chunks_fts WHERE rowid = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    DELETE FROM chunks_fts WHERE rowid = OLD.id;
    INSERT INTO chunks_fts(rowid, name, content)
    VALUES (NEW.id, NEW.name, NEW.content);
END;
"""


def init_index_database(db_path: str, embedding_dims: int) -> sqlite3.Connection:
    """Initialize index database with schema and extensions."""
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.executescript(get_index_schema_sql(embedding_dims))
    conn.executescript(INDEX_FTS_TRIGGERS)
    conn.commit()

    return conn
