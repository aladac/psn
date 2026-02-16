"""
Training file parser service.

Parses YAML and JSON-LD training files to extract memories.
"""

import json
from pathlib import Path

import yaml

from personality.schemas.training import (
    TrainingDocument,
    TrainingMemory,
)


class TrainingParser:
    """
    Service for parsing training files.

    Supports YAML and JSON-LD formats for defining agent memories.
    """

    def parse_file(self, path: Path) -> TrainingDocument:
        """
        Parse a training file.

        Args:
            path: Path to the training file.

        Returns:
            TrainingDocument with parsed memories.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If file format is unsupported.
        """
        if not path.exists():
            raise FileNotFoundError(f"Training file not found: {path}")

        suffix = path.suffix.lower()
        content = path.read_text(encoding="utf-8")

        if suffix in (".yml", ".yaml"):
            tag, version, memories, preferences = self._parse_yaml(content)
        elif suffix in (".jsonld", ".json"):
            tag, version, memories, preferences = self._parse_jsonld(content)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        return TrainingDocument(
            source=path,
            format=suffix.lstrip("."),
            tag=tag,
            version=version,
            memories=memories,
            preferences=preferences,
        )

    def _parse_yaml(self, content: str) -> tuple[str, str, list[TrainingMemory], dict]:
        """
        Parse YAML training content.

        Expected format:
        ```yaml
        tag: glados
        version: 3.11

        preferences:
          identity:
            agent: glados
          tts:
            enabled: true
            voice: glados

        memories:
          - subject: user.preference
            content: Some preference
        ```

        Args:
            content: YAML content string.

        Returns:
            Tuple of (tag, version, memories, preferences).
        """
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("YAML root must be a dictionary")

        # Extract tag and version
        tag = str(data.get("tag", ""))
        version = str(data.get("version", ""))

        memories: list[TrainingMemory] = []

        # Extract preferences (not stored as memories)
        preferences = data.get("preferences", {})
        if not isinstance(preferences, dict):
            preferences = {}

        # Parse identity section (legacy format)
        identity = data.get("identity", {})
        if isinstance(identity, dict):
            for key, value in identity.items():
                if value:
                    memories.append(
                        TrainingMemory(
                            subject=f"identity.{key}",
                            content=str(value),
                        )
                    )

        # Parse memories section
        memory_list = data.get("memories", [])
        if isinstance(memory_list, list):
            for item in memory_list:
                if isinstance(item, dict):
                    subject = item.get("subject", "")
                    mem_content = item.get("content", "")
                    if subject and mem_content:
                        # Handle list content (e.g., addressed_as)
                        if isinstance(mem_content, list):
                            mem_content = ", ".join(str(x) for x in mem_content)
                        memories.append(
                            TrainingMemory(
                                subject=str(subject),
                                content=str(mem_content),
                            )
                        )

        return tag, version, memories, preferences

    def _parse_jsonld(self, content: str) -> tuple[str, str, list[TrainingMemory], dict]:
        """
        Parse JSON-LD training content.

        Expected format:
        ```json
        {
          "@context": "...",
          "tag": "glados",
          "version": "3.11",
          "preferences": {
            "identity": {"agent": "glados"},
            "tts": {"enabled": true, "voice": "glados"}
          },
          "memories": [
            {"subject": "...", "content": "..."}
          ]
        }
        ```

        Args:
            content: JSON-LD content string.

        Returns:
            Tuple of (tag, version, memories, preferences).
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-LD: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("JSON-LD root must be an object")

        # Extract tag and version
        tag = str(data.get("tag", ""))
        version = str(data.get("version", ""))

        memories: list[TrainingMemory] = []

        # Extract preferences (not stored as memories)
        preferences = data.get("preferences", {})
        if not isinstance(preferences, dict):
            preferences = {}

        # Extract identity from top-level properties
        for key in ("name", "description", "personality", "purpose"):
            value = data.get(key)
            if value and isinstance(value, str):
                memories.append(
                    TrainingMemory(
                        subject=f"identity.{key}",
                        content=value,
                    )
                )

        # Parse memories array
        memory_list = data.get("memories", [])
        if isinstance(memory_list, list):
            for item in memory_list:
                if isinstance(item, dict):
                    subject = item.get("subject", "")
                    mem_content = item.get("content", "")
                    if subject and mem_content:
                        # Handle list content
                        if isinstance(mem_content, list):
                            mem_content = ", ".join(str(x) for x in mem_content)
                        memories.append(
                            TrainingMemory(
                                subject=str(subject),
                                content=str(mem_content),
                            )
                        )

        # Parse knowledge graph if present
        knowledge = data.get("knowledge", [])
        if isinstance(knowledge, list):
            for item in knowledge:
                if isinstance(item, dict):
                    subject = item.get("@type", "knowledge.general")
                    mem_content = item.get("description", "") or item.get("value", "")
                    if mem_content:
                        memories.append(
                            TrainingMemory(
                                subject=str(subject),
                                content=str(mem_content),
                            )
                        )

        return tag, version, memories, preferences

    def list_training_files(self, directory: Path) -> list[Path]:
        """
        List all training files in a directory.

        Args:
            directory: Directory to scan.

        Returns:
            List of training file paths.
        """
        if not directory.exists():
            return []

        files = []
        for pattern in ("*.yml", "*.yaml", "*.jsonld"):
            files.extend(directory.glob(pattern))

        return sorted(files, key=lambda p: p.stem.lower())

    def validate_file(self, path: Path) -> tuple[bool, str]:
        """
        Validate a training file.

        Args:
            path: Path to the training file.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            doc = self.parse_file(path)
            if doc.count == 0:
                return False, "No memories found in file"
            return True, f"Valid: {doc.count} memories, tag={doc.tag}"
        except FileNotFoundError:
            return False, f"File not found: {path}"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"
