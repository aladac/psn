"""Training-related Pydantic schemas."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TrainingMemory(BaseModel):
    """A single memory extracted from training data."""

    subject: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class TrainingDocument(BaseModel):
    """A parsed training document."""

    source: Path
    format: str  # yaml, jsonld, text
    tag: str = ""  # persona tag (e.g., "glados", "bt7274")
    version: str = ""  # persona version
    memories: list[TrainingMemory] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)

    @property
    def count(self) -> int:
        """Number of memories in document."""
        return len(self.memories)


class TrainingResult(BaseModel):
    """Result of a training operation."""

    documents_processed: int = Field(default=0, ge=0)
    memories_stored: int = Field(default=0, ge=0)
    duplicates_skipped: int = Field(default=0, ge=0)
    errors: list[str] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether training was successful (no errors)."""
        return len(self.errors) == 0

    @property
    def total_processed(self) -> int:
        """Total memories processed."""
        return self.memories_stored + self.duplicates_skipped
