"""
Memory extractor service.

Extracts learnings, preferences, and facts from conversation transcripts.
"""

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedMemory:
    """A memory extracted from a transcript."""

    subject: str
    content: str
    source: str = "transcript"
    confidence: float = 0.8
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()


# Patterns for extracting different types of information
EXTRACTION_PATTERNS = {
    # User preferences
    "user.preference": [
        r"(?:I |my |i )(?:prefer|like|want|always|usually|never)\s+(.+?)(?:\.|$)",
        r"(?:please |don't |do not )(.+?)(?:\.|$)",
    ],
    # User corrections
    "user.correction": [
        r"(?:actually|no,|wrong|incorrect|not quite|that's not right)[,:]?\s*(.+?)(?:\.|$)",
        r"(?:I meant|I mean|what I meant was)\s+(.+?)(?:\.|$)",
    ],
    # Project information
    "project.info": [
        r"(?:this project|the project|our project)\s+(?:is|uses|has)\s+(.+?)(?:\.|$)",
        r"(?:we're using|we use|we have)\s+(.+?)(?:\.|$)",
    ],
    # Technical facts
    "knowledge.tech": [
        r"(\w+)\s+(?:is|are)\s+(?:a |an |the )?([\w\s]+?)(?:\.|,|$)",
    ],
    # User identity
    "user.identity": [
        r"(?:my name is|I'm called|call me)\s+(\w+)",
        r"(?:I am|I'm)\s+(?:a |an )?([\w\s]+?)(?:\.|,|$)",
    ],
}

# Subject taxonomy prefixes
VALID_PREFIXES = ("user.", "self.", "project.", "knowledge.", "meta.")


class MemoryExtractor:
    """
    Extracts memories from conversation transcripts.

    Uses pattern matching to identify user preferences, corrections,
    facts, and other learnable information.
    """

    def __init__(self, min_confidence: float = 0.5) -> None:
        """
        Initialize the memory extractor.

        Args:
            min_confidence: Minimum confidence threshold for extraction.
        """
        self._min_confidence = min_confidence

    def extract_from_text(self, text: str) -> list[ExtractedMemory]:
        """
        Extract memories from plain text.

        Args:
            text: Text to extract from.

        Returns:
            List of extracted memories.
        """
        memories: list[ExtractedMemory] = []

        for subject, patterns in EXTRACTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    content = match.group(1).strip() if match.groups() else match.group(0).strip()

                    # Skip very short or very long matches
                    if len(content) < 5 or len(content) > 500:
                        continue

                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(subject, content)

                    if confidence >= self._min_confidence:
                        memories.append(
                            ExtractedMemory(
                                subject=subject,
                                content=content,
                                confidence=confidence,
                            )
                        )

        # Deduplicate similar memories
        return self._deduplicate(memories)

    def extract_from_transcript(self, transcript: list[dict]) -> list[ExtractedMemory]:
        """
        Extract memories from a structured transcript.

        Args:
            transcript: List of message dicts with 'role' and 'content'.

        Returns:
            List of extracted memories.
        """
        memories: list[ExtractedMemory] = []

        for msg in transcript:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if not content:
                continue

            # Higher confidence for user messages (direct statements)
            base_confidence = 0.9 if role == "user" else 0.7

            extracted = self.extract_from_text(content)
            for mem in extracted:
                mem.confidence *= base_confidence
                if mem.confidence >= self._min_confidence:
                    memories.append(mem)

        return self._deduplicate(memories)

    def categorize_memory(self, content: str, hint: str = "") -> str:
        """
        Categorize a piece of content into the subject taxonomy.

        Args:
            content: Content to categorize.
            hint: Optional hint for categorization.

        Returns:
            Subject string (e.g., 'user.preference').
        """
        content_lower = content.lower()

        # Check for explicit hints
        if hint:
            for prefix in VALID_PREFIXES:
                if hint.startswith(prefix):
                    return hint

        # Categorization heuristics
        if any(word in content_lower for word in ["prefer", "like", "want", "favorite"]):
            return "user.preference"

        if any(word in content_lower for word in ["name is", "i am", "i'm a"]):
            return "user.identity"

        if any(word in content_lower for word in ["project", "codebase", "repository"]):
            return "project.info"

        if any(word in content_lower for word in ["remember", "don't forget", "note that"]):
            return "meta.note"

        # Default to general knowledge
        return "knowledge.general"

    def _calculate_confidence(self, subject: str, content: str) -> float:
        """Calculate confidence score for an extraction."""
        base_confidence = 0.7

        # Boost confidence for specific patterns
        if subject.startswith("user."):
            base_confidence += 0.1  # User statements are more reliable

        if subject == "user.correction":
            base_confidence += 0.15  # Corrections are very explicit

        # Reduce confidence for very generic content
        if len(content.split()) < 3:
            base_confidence -= 0.2

        # Reduce confidence for content with uncertainty
        uncertainty_words = ["maybe", "perhaps", "might", "could", "possibly"]
        if any(word in content.lower() for word in uncertainty_words):
            base_confidence -= 0.2

        return max(0.1, min(1.0, base_confidence))

    def _deduplicate(self, memories: list[ExtractedMemory]) -> list[ExtractedMemory]:
        """Remove duplicate or very similar memories."""
        if not memories:
            return memories

        unique: list[ExtractedMemory] = []
        seen_content: set[str] = set()

        for mem in memories:
            # Normalize content for comparison
            normalized = mem.content.lower().strip()

            # Check for exact duplicates
            if normalized in seen_content:
                continue

            # Check for substring matches
            is_substring = False
            for seen in seen_content:
                if normalized in seen or seen in normalized:
                    is_substring = True
                    break

            if not is_substring:
                unique.append(mem)
                seen_content.add(normalized)

        return unique

    def merge_with_existing(
        self,
        extracted: list[ExtractedMemory],
        existing: list[dict],
    ) -> list[ExtractedMemory]:
        """
        Filter out memories that already exist.

        Args:
            extracted: Newly extracted memories.
            existing: Existing memories (with 'subject' and 'content' keys).

        Returns:
            Filtered list of new memories.
        """
        existing_content = {m.get("content", "").lower().strip() for m in existing}

        new_memories = []
        for mem in extracted:
            normalized = mem.content.lower().strip()
            if normalized not in existing_content:
                # Also check for high similarity
                is_similar = False
                for existing_c in existing_content:
                    if self._is_similar(normalized, existing_c):
                        is_similar = True
                        break
                if not is_similar:
                    new_memories.append(mem)

        return new_memories

    def _is_similar(self, a: str, b: str, threshold: float = 0.8) -> bool:
        """Check if two strings are similar using simple word overlap."""
        if not a or not b:
            return False

        words_a = set(a.split())
        words_b = set(b.split())

        if not words_a or not words_b:
            return False

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return (intersection / union) >= threshold if union > 0 else False
