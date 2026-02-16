"""Decision tracking schemas.

Track architectural and design decisions with rationale and alternatives.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DecisionStatus(StrEnum):
    """Status of a decision."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


class Decision(BaseModel):
    """An architectural or design decision."""

    id: str = Field(default="", description="Unique identifier")
    title: str = Field(..., min_length=1, description="Decision title")
    context: str = Field(default="", description="Context and background")
    decision: str = Field(default="", description="The decision made")
    rationale: str = Field(default="", description="Why this decision was made")
    alternatives: list[str] = Field(default_factory=list, description="Alternatives considered")
    consequences: list[str] = Field(default_factory=list, description="Expected consequences")
    status: DecisionStatus = Field(default=DecisionStatus.PROPOSED)
    project: str = Field(default="", description="Project context")
    persona: str = Field(default="", description="Associated persona tag")
    tags: list[str] = Field(default_factory=list, description="Classification tags")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_adr(self) -> str:
        """Format as Architecture Decision Record (ADR)."""
        lines = [
            f"# {self.title}",
            "",
            f"**Status:** {self.status.value}",
            f"**Date:** {self.created_at.strftime('%Y-%m-%d')}",
            "",
        ]

        if self.context:
            lines.extend(["## Context", "", self.context, ""])

        if self.decision:
            lines.extend(["## Decision", "", self.decision, ""])

        if self.rationale:
            lines.extend(["## Rationale", "", self.rationale, ""])

        if self.alternatives:
            lines.extend(["## Alternatives Considered", ""])
            for alt in self.alternatives:
                lines.append(f"- {alt}")
            lines.append("")

        if self.consequences:
            lines.extend(["## Consequences", ""])
            for cons in self.consequences:
                lines.append(f"- {cons}")
            lines.append("")

        return "\n".join(lines)

    def summary(self) -> str:
        """Brief summary of the decision."""
        status_emoji = {
            DecisionStatus.PROPOSED: "?",
            DecisionStatus.ACCEPTED: "+",
            DecisionStatus.REJECTED: "x",
            DecisionStatus.SUPERSEDED: "~",
            DecisionStatus.DEPRECATED: "-",
        }
        emoji = status_emoji.get(self.status, "?")
        return f"[{emoji}] {self.title}"


class DecisionStore(BaseModel):
    """Container for decisions with metadata."""

    version: int = 1
    persona: str = ""
    project: str = ""
    decisions: list[Decision] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def count(self) -> int:
        """Number of decisions."""
        return len(self.decisions)

    def add(self, decision: Decision) -> None:
        """Add a decision to the store."""
        self.decisions.append(decision)
        self.updated_at = datetime.now()

    def find_by_id(self, decision_id: str) -> Decision | None:
        """Find a decision by ID."""
        for d in self.decisions:
            if d.id == decision_id:
                return d
        return None

    def find_by_status(self, status: DecisionStatus) -> list[Decision]:
        """Find decisions by status."""
        return [d for d in self.decisions if d.status == status]

    def find_by_tag(self, tag: str) -> list[Decision]:
        """Find decisions by tag."""
        tag_lower = tag.lower()
        return [d for d in self.decisions if tag_lower in [t.lower() for t in d.tags]]

    def remove(self, decision_id: str) -> bool:
        """Remove a decision by ID."""
        original_count = len(self.decisions)
        self.decisions = [d for d in self.decisions if d.id != decision_id]
        if len(self.decisions) < original_count:
            self.updated_at = datetime.now()
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "persona": self.persona,
            "project": self.project,
            "decisions": [d.model_dump(mode="json") for d in self.decisions],
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionStore":
        """Create from dictionary."""
        decisions = [Decision(**d) for d in data.get("decisions", [])]
        return cls(
            version=data.get("version", 1),
            persona=data.get("persona", ""),
            project=data.get("project", ""),
            decisions=decisions,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )
