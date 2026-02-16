"""
Memory pruner service.

Removes stale or low-value memories based on scoring criteria.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PruneResult:
    """Result of a pruning operation."""

    total_count: int = 0
    pruned_count: int = 0
    archived_count: int = 0
    retained_count: int = 0
    pruned_memories: list[dict] = field(default_factory=list)

    @property
    def pruned_percent(self) -> float:
        """Percentage of memories pruned."""
        if self.total_count == 0:
            return 0.0
        return (self.pruned_count / self.total_count) * 100


@dataclass
class MemoryScore:
    """Score breakdown for a memory."""

    memory_id: str
    recency_score: float = 0.0
    access_score: float = 0.0
    relevance_score: float = 0.0
    total_score: float = 0.0

    def calculate_total(
        self,
        recency_weight: float = 0.4,
        access_weight: float = 0.3,
        relevance_weight: float = 0.3,
    ) -> float:
        """Calculate weighted total score."""
        self.total_score = (
            self.recency_score * recency_weight
            + self.access_score * access_weight
            + self.relevance_score * relevance_weight
        )
        return self.total_score


# Subject prefixes that should be preserved (higher retention)
PROTECTED_PREFIXES = (
    "user.identity",
    "user.preference",
    "self.identity",
    "self.protocol",
)

# Subject prefixes that can be pruned more aggressively
EPHEMERAL_PREFIXES = (
    "meta.note",
    "meta.context",
    "project.temp",
)


class MemoryPruner:
    """
    Prunes low-value memories based on scoring criteria.

    Scores memories by recency, access frequency, and relevance,
    then archives or removes those below threshold.
    """

    def __init__(
        self,
        prune_threshold: float = 0.3,
        max_age_days: int = 90,
        min_access_count: int = 0,
    ) -> None:
        """
        Initialize the pruner.

        Args:
            prune_threshold: Score threshold below which to prune.
            max_age_days: Maximum age before reducing recency score.
            min_access_count: Minimum access count to boost score.
        """
        self._prune_threshold = prune_threshold
        self._max_age_days = max_age_days
        self._min_access_count = min_access_count

    def prune(
        self,
        memories: list[dict],
        archive: bool = True,
    ) -> tuple[list[dict], list[dict], PruneResult]:
        """
        Prune low-value memories.

        Args:
            memories: List of memory dicts.
            archive: If True, return pruned memories for archival.

        Returns:
            Tuple of (retained memories, pruned/archived memories, result stats).
        """
        result = PruneResult(total_count=len(memories))

        if not memories:
            return [], [], result

        # Score all memories
        scores = [self.score_memory(mem) for mem in memories]

        # Separate retained and pruned
        retained: list[dict] = []
        pruned: list[dict] = []

        for mem, score in zip(memories, scores, strict=True):
            subject = mem.get("subject", "")

            # Protected subjects get a score boost
            if subject.startswith(PROTECTED_PREFIXES):
                score.total_score = min(1.0, score.total_score + 0.3)

            # Ephemeral subjects get a score penalty
            if subject.startswith(EPHEMERAL_PREFIXES):
                score.total_score = max(0.0, score.total_score - 0.2)

            if score.total_score >= self._prune_threshold:
                retained.append(mem)
            else:
                pruned.append(mem)
                result.pruned_memories.append(
                    {
                        "id": mem.get("id", ""),
                        "subject": subject,
                        "score": score.total_score,
                    }
                )

        result.retained_count = len(retained)
        result.pruned_count = len(pruned)
        result.archived_count = len(pruned) if archive else 0

        return retained, pruned, result

    def score_memory(self, memory: dict) -> MemoryScore:
        """
        Calculate score for a memory.

        Args:
            memory: Memory dict with metadata.

        Returns:
            MemoryScore with component scores.
        """
        score = MemoryScore(memory_id=memory.get("id", ""))

        # Recency score (1.0 for new, decays over time)
        score.recency_score = self._calculate_recency_score(memory)

        # Access score (based on access_count if available)
        score.access_score = self._calculate_access_score(memory)

        # Relevance score (based on subject importance)
        score.relevance_score = self._calculate_relevance_score(memory)

        # Calculate weighted total
        score.calculate_total()

        return score

    def get_prune_candidates(
        self,
        memories: list[dict],
        limit: int = 10,
    ) -> list[tuple[dict, MemoryScore]]:
        """
        Get candidates for pruning without actually pruning.

        Args:
            memories: List of memory dicts.
            limit: Maximum candidates to return.

        Returns:
            List of (memory, score) tuples, sorted by score ascending.
        """
        scored = [(mem, self.score_memory(mem)) for mem in memories]

        # Sort by total score ascending (lowest first)
        scored.sort(key=lambda x: x[1].total_score)

        return scored[:limit]

    def should_prune(self, memory: dict) -> bool:
        """
        Check if a single memory should be pruned.

        Args:
            memory: Memory dict.

        Returns:
            True if memory should be pruned.
        """
        score = self.score_memory(memory)
        subject = memory.get("subject", "")

        # Apply subject modifiers
        if subject.startswith(PROTECTED_PREFIXES):
            score.total_score = min(1.0, score.total_score + 0.3)
        if subject.startswith(EPHEMERAL_PREFIXES):
            score.total_score = max(0.0, score.total_score - 0.2)

        return score.total_score < self._prune_threshold

    def _calculate_recency_score(self, memory: dict) -> float:
        """Calculate recency score based on created_at."""
        created_at = memory.get("created_at")

        if not created_at:
            return 0.5  # Default for unknown age

        # Parse datetime if string
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                return 0.5

        if not isinstance(created_at, datetime):
            return 0.5

        # Calculate age in days
        now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
        age_days = (now - created_at).days

        if age_days <= 0:
            return 1.0
        elif age_days >= self._max_age_days:
            return 0.1
        else:
            # Linear decay
            return 1.0 - (age_days / self._max_age_days) * 0.9

    def _calculate_access_score(self, memory: dict) -> float:
        """Calculate access score based on access_count."""
        access_count = memory.get("access_count", 0)

        if access_count <= 0:
            return 0.3  # Low score for never-accessed

        if access_count >= 10:
            return 1.0  # Max score for frequently accessed

        # Scale from 0.3 to 1.0
        return 0.3 + (access_count / 10) * 0.7

    def _calculate_relevance_score(self, memory: dict) -> float:
        """Calculate relevance score based on subject."""
        subject = memory.get("subject", "")

        # High relevance subjects
        if subject.startswith(("user.identity", "self.identity", "self.protocol")):
            return 1.0

        # Medium-high relevance
        if subject.startswith(("user.preference", "self.trait", "project.info")):
            return 0.8

        # Medium relevance
        if subject.startswith(("knowledge.", "self.")):
            return 0.6

        # Lower relevance
        if subject.startswith(("meta.", "project.temp")):
            return 0.4

        # Default
        return 0.5

    def estimate_savings(
        self,
        memories: list[dict],
        avg_memory_size: int = 200,
    ) -> dict:
        """
        Estimate storage savings from pruning.

        Args:
            memories: List of memories to analyze.
            avg_memory_size: Average memory size in bytes.

        Returns:
            Dict with savings estimates.
        """
        _, pruned, result = self.prune(memories, archive=False)

        return {
            "total_count": result.total_count,
            "prune_count": result.pruned_count,
            "prune_percent": result.pruned_percent,
            "estimated_bytes_freed": result.pruned_count * avg_memory_size,
            "retained_count": result.retained_count,
        }
