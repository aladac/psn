"""Diagnostic utilities for personality system."""

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from personality.config import CONFIG_DIR


@dataclass
class MemoryInfo:
    """Memory entry information."""

    id: int
    subject: str
    content: str
    source: str
    created_at: str
    accessed_at: str
    access_count: int


def get_memory_db(cart: str = "bt7274") -> Path:
    """Get path to memory database for a cart."""
    return CONFIG_DIR / "memory" / f"{cart}.db"


def list_memories(cart: str = "bt7274", subject_filter: str | None = None) -> list[MemoryInfo]:
    """List all memories, optionally filtered by subject prefix."""
    db_path = get_memory_db(cart)
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    if subject_filter:
        cursor = conn.execute(
            "SELECT id, subject, content, source, created_at, accessed_at, access_count "
            "FROM memories WHERE subject LIKE ?",
            (f"{subject_filter}%",),
        )
    else:
        cursor = conn.execute(
            "SELECT id, subject, content, source, created_at, accessed_at, access_count FROM memories"
        )

    memories = [MemoryInfo(*row) for row in cursor.fetchall()]
    conn.close()
    return memories


def memory_stats(cart: str = "bt7274") -> dict:
    """Get memory statistics by subject prefix."""
    memories = list_memories(cart)
    stats: dict[str, int] = {}

    for mem in memories:
        prefix = mem.subject.split(".")[0] if "." in mem.subject else mem.subject
        stats[prefix] = stats.get(prefix, 0) + 1

    return {
        "total": len(memories),
        "by_prefix": stats,
        "db_path": str(get_memory_db(cart)),
    }


def find_similar_memories(cart: str = "bt7274", threshold: float = 0.9) -> list[tuple[MemoryInfo, MemoryInfo, float]]:
    """Find potentially duplicate memories using content similarity."""
    memories = list_memories(cart)
    similar = []

    for i, m1 in enumerate(memories):
        for m2 in memories[i + 1 :]:
            # Simple Jaccard similarity on words
            words1 = set(m1.content.lower().split())
            words2 = set(m2.content.lower().split())
            if not words1 or not words2:
                continue
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            similarity = intersection / union if union else 0
            if similarity >= threshold:
                similar.append((m1, m2, similarity))

    return sorted(similar, key=lambda x: x[2], reverse=True)


@dataclass
class IndexInfo:
    """Project index information."""

    project_path: str
    db_path: str
    db_size: int
    file_count: int
    chunk_count: int
    last_modified: datetime
    exists: bool


def list_project_indexes() -> list[IndexInfo]:
    """List all project indexes with health info."""
    import json

    from personality.index.indexer import REGISTRY_FILE

    if not REGISTRY_FILE.exists():
        return []

    registry = json.loads(REGISTRY_FILE.read_text())
    indexes = []

    for project_path, db_path in registry.items():
        db_file = Path(db_path)
        exists = db_file.exists()
        db_size = db_file.stat().st_size if exists else 0
        last_modified = datetime.fromtimestamp(db_file.stat().st_mtime) if exists else datetime.min

        file_count = 0
        chunk_count = 0
        if exists:
            try:
                conn = sqlite3.connect(db_file)
                file_count = conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]
                chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
                conn.close()
            except Exception:
                pass

        indexes.append(
            IndexInfo(
                project_path=project_path,
                db_path=db_path,
                db_size=db_size,
                file_count=file_count,
                chunk_count=chunk_count,
                last_modified=last_modified,
                exists=exists,
            )
        )

    return indexes


def find_orphaned_indexes() -> list[IndexInfo]:
    """Find indexes for projects that no longer exist."""
    indexes = list_project_indexes()
    return [idx for idx in indexes if not Path(idx.project_path).exists()]


def find_stale_indexes(days: int = 30) -> list[IndexInfo]:
    """Find indexes not updated in specified days."""
    indexes = list_project_indexes()
    cutoff = datetime.now().timestamp() - (days * 86400)
    return [idx for idx in indexes if idx.last_modified.timestamp() < cutoff]


def cleanup_orphaned_indexes() -> list[str]:
    """Remove indexes for non-existent projects."""
    import json

    from personality.index.indexer import REGISTRY_FILE

    orphaned = find_orphaned_indexes()
    removed = []

    if not orphaned:
        return removed

    registry = json.loads(REGISTRY_FILE.read_text())
    for idx in orphaned:
        db_file = Path(idx.db_path)
        if db_file.exists():
            db_file.unlink()
        if idx.project_path in registry:
            del registry[idx.project_path]
        removed.append(idx.project_path)

    REGISTRY_FILE.write_text(json.dumps(registry, indent=2))
    return removed


def get_hooks_log() -> Path:
    """Get path to hooks log file."""
    return CONFIG_DIR / "hooks.log"


@dataclass
class LogEntry:
    """Parsed log entry."""

    timestamp: str
    level: str
    event: str
    message: str
    raw: str


def parse_log_line(line: str) -> LogEntry | None:
    """Parse a log line into structured entry."""
    # Format: 2024-01-15 10:30:45 INFO session-start: message
    parts = line.strip().split(" ", 3)
    if len(parts) < 4:
        return None

    try:
        timestamp = f"{parts[0]} {parts[1]}"
        level = parts[2]
        rest = parts[3] if len(parts) > 3 else ""
        event, _, message = rest.partition(": ")
        return LogEntry(timestamp=timestamp, level=level, event=event, message=message, raw=line)
    except Exception:
        return LogEntry(timestamp="", level="", event="", message=line, raw=line)


def tail_logs(lines: int = 50, event_filter: str | None = None) -> list[LogEntry]:
    """Get recent log entries."""
    log_file = get_hooks_log()
    if not log_file.exists():
        return []

    all_lines = log_file.read_text().strip().split("\n")
    entries = []

    for line in all_lines[-lines * 2 :]:  # Read extra to account for filtering
        entry = parse_log_line(line)
        if entry:
            if event_filter and event_filter not in entry.event:
                continue
            entries.append(entry)

    return entries[-lines:]


def get_log_stats() -> dict:
    """Get log statistics."""
    log_file = get_hooks_log()
    if not log_file.exists():
        return {"exists": False}

    entries = tail_logs(lines=1000)
    events: dict[str, int] = {}
    levels: dict[str, int] = {}

    for entry in entries:
        events[entry.event] = events.get(entry.event, 0) + 1
        levels[entry.level] = levels.get(entry.level, 0) + 1

    return {
        "exists": True,
        "size": log_file.stat().st_size,
        "total_entries": len(entries),
        "by_event": events,
        "by_level": levels,
    }


@dataclass
class EmbeddingStats:
    """Embedding system statistics."""

    available: bool
    model: str
    latency_ms: float
    dimensions: int
    error: str | None = None


def test_embeddings() -> EmbeddingStats:
    """Test embedding system connectivity and performance."""
    from personality.memory.embedder import Embedder

    try:
        embedder = Embedder()
        start = time.time()
        embedding = embedder.embed("test embedding latency")
        latency = (time.time() - start) * 1000

        return EmbeddingStats(
            available=True,
            model=embedder.model,
            latency_ms=round(latency, 1),
            dimensions=len(embedding),
        )
    except Exception as e:
        return EmbeddingStats(
            available=False,
            model="unknown",
            latency_ms=0,
            dimensions=0,
            error=str(e),
        )
