"""Knowledge graph schemas.

Stores subject-predicate-object triples for structured knowledge.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeTriple(BaseModel):
    """A single knowledge triple (subject-predicate-object)."""

    id: str = Field(default="", description="Unique identifier")
    subject: str = Field(..., min_length=1, description="Subject of the triple")
    predicate: str = Field(..., min_length=1, description="Relationship/predicate")
    object: str = Field(..., min_length=1, description="Object of the triple")
    project: str = Field(default="", description="Project context")
    persona: str = Field(default="", description="Associated persona tag")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    source: str = Field(default="", description="Source of the knowledge")
    created_at: datetime = Field(default_factory=datetime.now)

    def to_sentence(self) -> str:
        """Convert triple to natural language sentence."""
        return f"{self.subject} {self.predicate} {self.object}"

    def matches(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        obj: str | None = None,
    ) -> bool:
        """Check if triple matches the given filters."""
        if subject and subject.lower() not in self.subject.lower():
            return False
        if predicate and predicate.lower() not in self.predicate.lower():
            return False
        return not (obj and obj.lower() not in self.object.lower())


class KnowledgeStore(BaseModel):
    """Container for knowledge triples with metadata."""

    version: int = 1
    persona: str = ""
    project: str = ""
    triples: list[KnowledgeTriple] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def count(self) -> int:
        """Number of triples."""
        return len(self.triples)

    def add(self, triple: KnowledgeTriple) -> None:
        """Add a triple to the store."""
        self.triples.append(triple)
        self.updated_at = datetime.now()

    def find(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        obj: str | None = None,
    ) -> list[KnowledgeTriple]:
        """Find triples matching filters."""
        return [t for t in self.triples if t.matches(subject, predicate, obj)]

    def remove(self, triple_id: str) -> bool:
        """Remove a triple by ID."""
        original_count = len(self.triples)
        self.triples = [t for t in self.triples if t.id != triple_id]
        if len(self.triples) < original_count:
            self.updated_at = datetime.now()
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "persona": self.persona,
            "project": self.project,
            "triples": [t.model_dump(mode="json") for t in self.triples],
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeStore":
        """Create from dictionary."""
        triples = [KnowledgeTriple(**t) for t in data.get("triples", [])]
        return cls(
            version=data.get("version", 1),
            persona=data.get("persona", ""),
            project=data.get("project", ""),
            triples=triples,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )
