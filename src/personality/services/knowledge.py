"""
Knowledge service for managing subject-predicate-object triples.

Provides file-based storage for structured knowledge with
CRUD operations and basic search capabilities.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from personality.schemas.knowledge import KnowledgeStore, KnowledgeTriple

# Default storage location
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
KNOWLEDGE_FILE = "knowledge.json"


class KnowledgeService:
    """
    Service for managing knowledge triples.

    Stores knowledge in a JSON file with support for filtering
    and basic text search.
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        persona: str = "",
        project: str = "",
    ) -> None:
        """
        Initialize the knowledge service.

        Args:
            data_dir: Directory for storing knowledge data.
            persona: Default persona tag for new triples.
            project: Default project context for new triples.
        """
        self._data_dir = data_dir or DATA_DIR
        self._persona = persona
        self._project = project
        self._store: KnowledgeStore | None = None

    @property
    def store_path(self) -> Path:
        """Get the path to the knowledge store file."""
        return self._data_dir / KNOWLEDGE_FILE

    def _load_store(self) -> KnowledgeStore:
        """Load the knowledge store from disk."""
        if self._store is not None:
            return self._store

        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                self._store = KnowledgeStore.from_dict(data)
            except Exception:
                self._store = KnowledgeStore(persona=self._persona, project=self._project)
        else:
            self._store = KnowledgeStore(persona=self._persona, project=self._project)

        return self._store

    def _save_store(self) -> None:
        """Save the knowledge store to disk."""
        if self._store is None:
            return

        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = self._store.to_dict()
        self.store_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def add(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        persona: str | None = None,
        project: str | None = None,
        confidence: float = 1.0,
        source: str = "",
    ) -> KnowledgeTriple:
        """
        Add a knowledge triple.

        Args:
            subject: Subject of the triple.
            predicate: Relationship/predicate.
            obj: Object of the triple.
            persona: Associated persona (defaults to service persona).
            project: Project context (defaults to service project).
            confidence: Confidence score (0.0-1.0).
            source: Source of the knowledge.

        Returns:
            The created KnowledgeTriple.
        """
        store = self._load_store()

        triple = KnowledgeTriple(
            id=str(uuid.uuid4())[:8],
            subject=subject,
            predicate=predicate,
            object=obj,
            persona=persona or self._persona,
            project=project or self._project,
            confidence=confidence,
            source=source,
            created_at=datetime.now(),
        )

        store.add(triple)
        self._save_store()

        return triple

    def query(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        obj: str | None = None,
        persona: str | None = None,
    ) -> list[KnowledgeTriple]:
        """
        Query knowledge triples by filters.

        Args:
            subject: Filter by subject (partial match).
            predicate: Filter by predicate (partial match).
            obj: Filter by object (partial match).
            persona: Filter by persona.

        Returns:
            List of matching triples.
        """
        store = self._load_store()
        results = store.find(subject, predicate, obj)

        if persona:
            results = [t for t in results if t.persona == persona]

        return results

    def search(self, query: str, limit: int = 10) -> list[KnowledgeTriple]:
        """
        Search knowledge triples by text.

        Performs simple text matching across subject, predicate, and object.

        Args:
            query: Search query.
            limit: Maximum results to return.

        Returns:
            List of matching triples, sorted by relevance.
        """
        store = self._load_store()
        query_lower = query.lower()

        # Score each triple by how many fields match
        scored: list[tuple[int, KnowledgeTriple]] = []
        for triple in store.triples:
            score = 0
            if query_lower in triple.subject.lower():
                score += 3  # Subject match is most important
            if query_lower in triple.object.lower():
                score += 2  # Object match is second
            if query_lower in triple.predicate.lower():
                score += 1  # Predicate match is least important

            if score > 0:
                scored.append((score, triple))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [t for _, t in scored[:limit]]

    def list_all(self, limit: int = 100) -> list[KnowledgeTriple]:
        """
        List all knowledge triples.

        Args:
            limit: Maximum results to return.

        Returns:
            List of triples, most recent first.
        """
        store = self._load_store()
        # Sort by created_at descending
        sorted_triples = sorted(store.triples, key=lambda t: t.created_at, reverse=True)
        return sorted_triples[:limit]

    def get(self, triple_id: str) -> KnowledgeTriple | None:
        """
        Get a triple by ID.

        Args:
            triple_id: The triple ID.

        Returns:
            The triple or None if not found.
        """
        store = self._load_store()
        for triple in store.triples:
            if triple.id == triple_id:
                return triple
        return None

    def remove(self, triple_id: str) -> bool:
        """
        Remove a triple by ID.

        Args:
            triple_id: The triple ID.

        Returns:
            True if removed, False if not found.
        """
        store = self._load_store()
        if store.remove(triple_id):
            self._save_store()
            return True
        return False

    def clear(self) -> int:
        """
        Clear all knowledge triples.

        Returns:
            Number of triples removed.
        """
        store = self._load_store()
        count = len(store.triples)
        store.triples = []
        store.updated_at = datetime.now()
        self._save_store()
        return count

    def count(self) -> int:
        """Get the number of triples."""
        store = self._load_store()
        return store.count

    def subjects(self) -> list[str]:
        """Get unique subjects."""
        store = self._load_store()
        return sorted({t.subject for t in store.triples})

    def predicates(self) -> list[str]:
        """Get unique predicates."""
        store = self._load_store()
        return sorted({t.predicate for t in store.triples})

    def export_sentences(self) -> list[str]:
        """Export all triples as sentences."""
        store = self._load_store()
        return [t.to_sentence() for t in store.triples]
