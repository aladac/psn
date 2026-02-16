"""Pcart (Personality Cartridge) schemas.

A .pcart file is a ZIP archive containing:
- persona.yml: Core identity and memories
- preferences.yml: User preferences (never overwritten)
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from personality.schemas.training import TrainingMemory


class IdentityConfig(BaseModel):
    """Identity configuration from persona.yml."""

    agent: str = ""
    name: str = ""
    full_name: str = ""
    version: str = ""
    type: str = ""
    source: str = ""
    tagline: str = ""


class TTSConfig(BaseModel):
    """TTS configuration."""

    enabled: bool = True
    voice: str = ""


class PreferencesConfig(BaseModel):
    """User preferences from preferences.yml."""

    identity: IdentityConfig = Field(default_factory=IdentityConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreferencesConfig":
        """Create from dictionary, handling extra fields."""
        identity_data = data.get("identity", {})
        tts_data = data.get("tts", {})

        # Extract known fields
        known_keys = {"identity", "tts"}
        extra = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            identity=IdentityConfig(**identity_data) if identity_data else IdentityConfig(),
            tts=TTSConfig(**tts_data) if tts_data else TTSConfig(),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {}
        if self.identity.agent or self.identity.name:
            result["identity"] = {k: v for k, v in self.identity.model_dump().items() if v}
        if self.tts.enabled or self.tts.voice:
            result["tts"] = self.tts.model_dump()
        result.update(self.extra)
        return result


class PersonaConfig(BaseModel):
    """Persona configuration from persona.yml."""

    tag: str
    version: str = ""
    memories: list[TrainingMemory] = Field(default_factory=list)

    @property
    def memory_count(self) -> int:
        """Number of memories."""
        return len(self.memories)


class CartManifest(BaseModel):
    """Manifest metadata for a cartridge."""

    schema_version: int = 1
    tag: str
    version: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    memory_count: int = 0


class Cartridge(BaseModel):
    """A loaded personality cartridge."""

    path: Path | None = None
    manifest: CartManifest
    persona: PersonaConfig
    preferences: PreferencesConfig

    class Config:
        arbitrary_types_allowed = True

    @property
    def tag(self) -> str:
        """Persona tag."""
        return self.manifest.tag

    @property
    def name(self) -> str:
        """Display name."""
        return self.preferences.identity.name or self.manifest.tag

    @property
    def voice(self) -> str:
        """TTS voice."""
        return self.preferences.tts.voice

    @property
    def memory_count(self) -> int:
        """Number of memories."""
        return self.persona.memory_count
