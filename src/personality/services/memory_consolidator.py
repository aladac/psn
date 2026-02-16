"""
Memory consolidator service.

Merges related memories to reduce count while preserving key information.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConsolidationResult:
    """Result of a consolidation operation."""

    original_count: int = 0
    merged_count: int = 0
    final_count: int = 0
    groups_merged: int = 0
    memories_affected: list[str] = field(default_factory=list)

    @property
    def reduction(self) -> int:
        """Number of memories reduced."""
        return self.original_count - self.final_count

    @property
    def reduction_percent(self) -> float:
        """Percentage reduction."""
        if self.original_count == 0:
            return 0.0
        return (self.reduction / self.original_count) * 100


@dataclass
class MemoryGroup:
    """A group of related memories."""

    subject_prefix: str
    memories: list[dict] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.memories)

    def add(self, memory: dict) -> None:
        self.memories.append(memory)


class MemoryConsolidator:
    """
    Consolidates related memories to reduce total count.

    Groups memories by subject prefix and merges those with
    similar content while preserving key facts.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        min_group_size: int = 2,
        max_merged_length: int = 500,
    ) -> None:
        """
        Initialize the consolidator.

        Args:
            similarity_threshold: Threshold for considering memories similar.
            min_group_size: Minimum group size to trigger consolidation.
            max_merged_length: Maximum length of merged content.
        """
        self._similarity_threshold = similarity_threshold
        self._min_group_size = min_group_size
        self._max_merged_length = max_merged_length

    def consolidate(self, memories: list[dict]) -> tuple[list[dict], ConsolidationResult]:
        """
        Consolidate a list of memories.

        Args:
            memories: List of memory dicts with 'subject' and 'content'.

        Returns:
            Tuple of (consolidated memories, result stats).
        """
        result = ConsolidationResult(original_count=len(memories))

        if len(memories) < self._min_group_size:
            result.final_count = len(memories)
            return memories, result

        # Group memories by subject prefix
        groups = self._group_by_subject(memories)

        # Consolidate within each group
        consolidated: list[dict] = []
        for group in groups.values():
            if group.count < self._min_group_size:
                # Keep ungrouped memories as-is
                consolidated.extend(group.memories)
            else:
                # Find similar memories within group
                merged, count = self._merge_similar(group.memories)
                consolidated.extend(merged)
                if count > 0:
                    result.groups_merged += 1
                    result.merged_count += count

        result.final_count = len(consolidated)
        return consolidated, result

    def find_similar_pairs(self, memories: list[dict]) -> list[tuple[dict, dict, float]]:
        """
        Find pairs of similar memories.

        Args:
            memories: List of memory dicts.

        Returns:
            List of (memory1, memory2, similarity_score) tuples.
        """
        pairs: list[tuple[dict, dict, float]] = []

        for i, mem1 in enumerate(memories):
            for mem2 in memories[i + 1 :]:
                # Only compare memories with same subject prefix
                subj1 = mem1.get("subject", "").split(".")[0]
                subj2 = mem2.get("subject", "").split(".")[0]

                if subj1 != subj2:
                    continue

                similarity = self._calculate_similarity(
                    mem1.get("content", ""),
                    mem2.get("content", ""),
                )

                if similarity >= self._similarity_threshold:
                    pairs.append((mem1, mem2, similarity))

        # Sort by similarity descending
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs

    def merge_memories(self, mem1: dict, mem2: dict) -> dict:
        """
        Merge two memories into one.

        Args:
            mem1: First memory.
            mem2: Second memory.

        Returns:
            Merged memory dict.
        """
        content1 = mem1.get("content", "")
        content2 = mem2.get("content", "")

        # Combine content, removing duplicates
        merged_content = self._combine_content(content1, content2)

        # Use the more specific subject
        subject1 = mem1.get("subject", "")
        subject2 = mem2.get("subject", "")
        subject = subject1 if len(subject1) >= len(subject2) else subject2

        return {
            "subject": subject,
            "content": merged_content,
            "merged_from": [mem1.get("id"), mem2.get("id")],
            "merged_at": datetime.now().isoformat(),
        }

    def _group_by_subject(self, memories: list[dict]) -> dict[str, MemoryGroup]:
        """Group memories by subject prefix."""
        groups: dict[str, MemoryGroup] = {}

        for mem in memories:
            subject = mem.get("subject", "")
            # Get first two parts of subject (e.g., "user.preference")
            parts = subject.split(".")
            prefix = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]

            if prefix not in groups:
                groups[prefix] = MemoryGroup(subject_prefix=prefix)
            groups[prefix].add(mem)

        return groups

    def _merge_similar(self, memories: list[dict]) -> tuple[list[dict], int]:
        """
        Merge similar memories within a group.

        Returns:
            Tuple of (merged list, number of merges performed).
        """
        if len(memories) < 2:
            return memories, 0

        # Track which memories have been merged
        merged_indices: set[int] = set()
        result: list[dict] = []
        merge_count = 0

        for i, mem1 in enumerate(memories):
            if i in merged_indices:
                continue

            # Find best match for this memory
            best_match_idx = -1
            best_similarity = 0.0

            for j, mem2 in enumerate(memories[i + 1 :], start=i + 1):
                if j in merged_indices:
                    continue

                similarity = self._calculate_similarity(
                    mem1.get("content", ""),
                    mem2.get("content", ""),
                )

                if similarity > best_similarity and similarity >= self._similarity_threshold:
                    best_similarity = similarity
                    best_match_idx = j

            if best_match_idx >= 0:
                # Merge the pair
                merged = self.merge_memories(mem1, memories[best_match_idx])
                result.append(merged)
                merged_indices.add(i)
                merged_indices.add(best_match_idx)
                merge_count += 1
            else:
                # No match found, keep original
                result.append(mem1)
                merged_indices.add(i)

        # Add any remaining unmerged memories
        for i, mem in enumerate(memories):
            if i not in merged_indices:
                result.append(mem)

        return result, merge_count

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using word overlap."""
        if not text1 or not text2:
            return 0.0

        # Normalize and tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of", "and", "or", "in", "on"}
        words1 -= stop_words
        words2 -= stop_words

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _combine_content(self, content1: str, content2: str) -> str:
        """Combine two content strings, removing duplicates."""
        # Split into sentences/phrases
        parts1 = [p.strip() for p in content1.split(".") if p.strip()]
        parts2 = [p.strip() for p in content2.split(".") if p.strip()]

        # Combine unique parts
        combined = []
        seen = set()

        for part in parts1 + parts2:
            normalized = part.lower()
            if normalized not in seen:
                combined.append(part)
                seen.add(normalized)

        result = ". ".join(combined)
        if result and not result.endswith("."):
            result += "."

        # Truncate if too long
        if len(result) > self._max_merged_length:
            result = result[: self._max_merged_length - 3] + "..."

        return result
