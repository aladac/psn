"""Database schema for document index with vector and full-text search."""

import sqlite3

import sqlite_vec

DOC_SCHEMA_VERSION = 1


def get_doc_schema_sql(embedding_dims: int) -> str:
    """Generate document schema SQL with correct embedding dimensions."""
    return f"""
-- Document metadata
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    title TEXT,
    source_url TEXT,
    fetched_at TEXT,
    file_hash TEXT NOT NULL,
    indexed_at TEXT DEFAULT (datetime('now'))
);

-- Document chunks
CREATE TABLE IF NOT EXISTS doc_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_type TEXT NOT NULL,
    heading TEXT,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    UNIQUE(document_id, chunk_type, heading, start_line)
);

-- Vector storage for chunks (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks_vec USING vec0(
    id INTEGER PRIMARY KEY,
    embedding FLOAT[{embedding_dims}]
);

-- Full-text search for chunks (FTS5 with porter stemmer)
CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks_fts USING fts5(
    heading,
    content,
    tokenize='porter'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_url);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc ON doc_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_type ON doc_chunks(chunk_type);

-- Schema version
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES ({DOC_SCHEMA_VERSION});
"""


DOC_FTS_TRIGGERS = """
-- Sync triggers for FTS
CREATE TRIGGER IF NOT EXISTS doc_chunks_ai AFTER INSERT ON doc_chunks BEGIN
    INSERT INTO doc_chunks_fts(rowid, heading, content)
    VALUES (NEW.id, NEW.heading, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS doc_chunks_ad AFTER DELETE ON doc_chunks BEGIN
    DELETE FROM doc_chunks_fts WHERE rowid = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS doc_chunks_au AFTER UPDATE ON doc_chunks BEGIN
    DELETE FROM doc_chunks_fts WHERE rowid = OLD.id;
    INSERT INTO doc_chunks_fts(rowid, heading, content)
    VALUES (NEW.id, NEW.heading, NEW.content);
END;
"""


def init_doc_database(db_path: str, embedding_dims: int) -> sqlite3.Connection:
    """Initialize document database with schema and extensions."""
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.executescript(get_doc_schema_sql(embedding_dims))
    conn.executescript(DOC_FTS_TRIGGERS)
    conn.commit()

    return conn
