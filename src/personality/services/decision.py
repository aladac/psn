"""
Decision service for tracking architectural and design decisions.

Provides file-based storage for decisions with ADR (Architecture Decision Record) format.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from personality.schemas.decision import Decision, DecisionStatus, DecisionStore

# Default storage location
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DECISIONS_FILE = "decisions.json"


class DecisionService:
    """
    Service for managing architectural decisions.

    Stores decisions in a JSON file with ADR-style formatting.
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        persona: str = "",
        project: str = "",
    ) -> None:
        """
        Initialize the decision service.

        Args:
            data_dir: Directory for storing decision data.
            persona: Default persona tag for new decisions.
            project: Default project context for new decisions.
        """
        self._data_dir = data_dir or DATA_DIR
        self._persona = persona
        self._project = project
        self._store: DecisionStore | None = None

    @property
    def store_path(self) -> Path:
        """Get the path to the decision store file."""
        return self._data_dir / DECISIONS_FILE

    def _load_store(self) -> DecisionStore:
        """Load the decision store from disk."""
        if self._store is not None:
            return self._store

        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                self._store = DecisionStore.from_dict(data)
            except Exception:
                self._store = DecisionStore(persona=self._persona, project=self._project)
        else:
            self._store = DecisionStore(persona=self._persona, project=self._project)

        return self._store

    def _save_store(self) -> None:
        """Save the decision store to disk."""
        if self._store is None:
            return

        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = self._store.to_dict()
        self.store_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def record(
        self,
        title: str,
        *,
        context: str = "",
        decision: str = "",
        rationale: str = "",
        alternatives: list[str] | None = None,
        consequences: list[str] | None = None,
        status: DecisionStatus = DecisionStatus.PROPOSED,
        tags: list[str] | None = None,
        persona: str | None = None,
        project: str | None = None,
    ) -> Decision:
        """
        Record a new decision.

        Args:
            title: Decision title.
            context: Context and background.
            decision: The decision made.
            rationale: Why this decision was made.
            alternatives: Alternatives considered.
            consequences: Expected consequences.
            status: Decision status.
            tags: Classification tags.
            persona: Associated persona.
            project: Project context.

        Returns:
            The created Decision.
        """
        store = self._load_store()

        dec = Decision(
            id=str(uuid.uuid4())[:8],
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
            alternatives=alternatives or [],
            consequences=consequences or [],
            status=status,
            tags=tags or [],
            persona=persona or self._persona,
            project=project or self._project,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        store.add(dec)
        self._save_store()

        return dec

    def get(self, decision_id: str) -> Decision | None:
        """
        Get a decision by ID.

        Args:
            decision_id: The decision ID.

        Returns:
            The decision or None if not found.
        """
        store = self._load_store()
        return store.find_by_id(decision_id)

    def list_all(
        self,
        status: DecisionStatus | None = None,
        project: str | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """
        List decisions with optional filters.

        Args:
            status: Filter by status.
            project: Filter by project.
            limit: Maximum results.

        Returns:
            List of decisions, most recent first.
        """
        store = self._load_store()

        results = store.decisions

        if status:
            results = [d for d in results if d.status == status]

        if project:
            results = [d for d in results if d.project == project]

        # Sort by created_at descending
        results = sorted(results, key=lambda d: d.created_at, reverse=True)

        return results[:limit]

    def search(self, query: str, limit: int = 10) -> list[Decision]:
        """
        Search decisions by text.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of matching decisions.
        """
        store = self._load_store()
        query_lower = query.lower()

        scored: list[tuple[int, Decision]] = []
        for dec in store.decisions:
            score = 0
            if query_lower in dec.title.lower():
                score += 3
            if query_lower in dec.context.lower():
                score += 2
            if query_lower in dec.decision.lower():
                score += 2
            if query_lower in dec.rationale.lower():
                score += 1
            if any(query_lower in t.lower() for t in dec.tags):
                score += 2

            if score > 0:
                scored.append((score, dec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:limit]]

    def update_status(self, decision_id: str, status: DecisionStatus) -> Decision | None:
        """
        Update a decision's status.

        Args:
            decision_id: The decision ID.
            status: New status.

        Returns:
            The updated decision or None if not found.
        """
        store = self._load_store()
        dec = store.find_by_id(decision_id)

        if dec:
            dec.status = status
            dec.updated_at = datetime.now()
            self._save_store()

        return dec

    def update(
        self,
        decision_id: str,
        *,
        title: str | None = None,
        context: str | None = None,
        decision: str | None = None,
        rationale: str | None = None,
        alternatives: list[str] | None = None,
        consequences: list[str] | None = None,
        status: DecisionStatus | None = None,
        tags: list[str] | None = None,
    ) -> Decision | None:
        """
        Update a decision.

        Args:
            decision_id: The decision ID.
            title: New title.
            context: New context.
            decision: New decision text.
            rationale: New rationale.
            alternatives: New alternatives.
            consequences: New consequences.
            status: New status.
            tags: New tags.

        Returns:
            The updated decision or None if not found.
        """
        store = self._load_store()
        dec = store.find_by_id(decision_id)

        if dec:
            if title is not None:
                dec.title = title
            if context is not None:
                dec.context = context
            if decision is not None:
                dec.decision = decision
            if rationale is not None:
                dec.rationale = rationale
            if alternatives is not None:
                dec.alternatives = alternatives
            if consequences is not None:
                dec.consequences = consequences
            if status is not None:
                dec.status = status
            if tags is not None:
                dec.tags = tags
            dec.updated_at = datetime.now()
            self._save_store()

        return dec

    def remove(self, decision_id: str) -> bool:
        """
        Remove a decision by ID.

        Args:
            decision_id: The decision ID.

        Returns:
            True if removed, False if not found.
        """
        store = self._load_store()
        if store.remove(decision_id):
            self._save_store()
            return True
        return False

    def count(self) -> int:
        """Get the number of decisions."""
        store = self._load_store()
        return store.count

    def count_by_status(self) -> dict[str, int]:
        """Get count of decisions by status."""
        store = self._load_store()
        counts: dict[str, int] = {}
        for dec in store.decisions:
            status = dec.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    def export_adr(self, decision_id: str) -> str | None:
        """
        Export a decision as ADR markdown.

        Args:
            decision_id: The decision ID.

        Returns:
            ADR markdown or None if not found.
        """
        dec = self.get(decision_id)
        return dec.to_adr() if dec else None

    def export_all_adr(self, output_dir: Path) -> int:
        """
        Export all decisions as ADR files.

        Args:
            output_dir: Directory for ADR files.

        Returns:
            Number of files exported.
        """
        store = self._load_store()
        output_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for i, dec in enumerate(sorted(store.decisions, key=lambda d: d.created_at), 1):
            filename = f"{i:04d}-{dec.title.lower().replace(' ', '-')[:50]}.md"
            filepath = output_dir / filename
            filepath.write_text(dec.to_adr(), encoding="utf-8")
            count += 1

        return count
