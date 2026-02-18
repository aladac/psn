"""PSN Configuration management.

Loads configuration from ~/.config/psn/config.toml with sensible defaults.
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Config file location
CONFIG_DIR = Path.home() / ".config" / "psn"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class RemoteConfig(BaseModel):
    """Remote host configuration."""

    host: str = Field(default="junkpile", description="Remote host for SSH connections")
    ssh_key: str = Field(
        default="~/.ssh/id_ed25519", description="SSH private key path"
    )

    @property
    def ssh_key_path(self) -> Path:
        """Expanded SSH key path."""
        return Path(self.ssh_key).expanduser()


class PostgresConfig(BaseModel):
    """PostgreSQL configuration."""

    host: str = Field(default="junkpile", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="personality", description="Default database name")
    user: str = Field(default="chi", description="PostgreSQL user")


class OllamaConfig(BaseModel):
    """Ollama configuration."""

    host: str = Field(default="junkpile", description="Ollama server host")
    port: int = Field(default=11434, description="Ollama server port")
    embedding_model: str = Field(
        default="nomic-ai/nomic-embed-text-v1.5", description="Default embedding model"
    )

    @property
    def url(self) -> str:
        """Full Ollama URL."""
        return f"http://{self.host}:{self.port}"


class TTSConfig(BaseModel):
    """Text-to-speech configuration."""

    voice: str = Field(default="en_US-lessac-medium", description="Default TTS voice")
    rate: float = Field(default=1.0, description="Speech rate multiplier")


class PathsConfig(BaseModel):
    """Path configuration."""

    homebrew: str = Field(
        default="/opt/homebrew/bin", description="Homebrew bin directory"
    )
    data_dir: str = Field(
        default="~/.local/share/psn", description="PSN data directory"
    )

    @property
    def data_path(self) -> Path:
        """Expanded data directory path."""
        return Path(self.data_dir).expanduser()


class PSNConfig(BaseModel):
    """Root PSN configuration."""

    remote: RemoteConfig = Field(default_factory=RemoteConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)


# Global config instance (lazy loaded)
_config: PSNConfig | None = None


def load_config() -> PSNConfig:
    """Load configuration from TOML file, with defaults for missing values."""
    global _config

    if _config is not None:
        return _config

    config_data: dict[str, Any] = {}

    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("rb") as f:
                config_data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            # Log error but continue with defaults
            import sys
            print(f"Warning: Failed to parse {CONFIG_FILE}: {e}", file=sys.stderr)

    _config = PSNConfig(**config_data)
    return _config


def get_config() -> PSNConfig:
    """Get the current configuration (loads if not already loaded)."""
    return load_config()


def reload_config() -> PSNConfig:
    """Force reload configuration from file."""
    global _config
    _config = None
    return load_config()


def ensure_config_dir() -> Path:
    """Ensure config directory exists and return its path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_default_config_toml() -> str:
    """Generate default config.toml content with comments."""
    return '''\
# PSN Configuration
# Location: ~/.config/psn/config.toml

[remote]
# Remote host for Docker, Ollama SSH connections
host = "junkpile"
ssh_key = "~/.ssh/id_ed25519"

[postgres]
# PostgreSQL connection settings
host = "junkpile"
port = 5432
database = "personality"
user = "chi"

[ollama]
# Ollama server for embeddings and generation
host = "junkpile"
port = 11434
embedding_model = "nomic-ai/nomic-embed-text-v1.5"

[tts]
# Text-to-speech settings
voice = "en_US-lessac-medium"
rate = 1.0

[paths]
# System paths
homebrew = "/opt/homebrew/bin"
data_dir = "~/.local/share/psn"
'''


def init_config(overwrite: bool = False) -> tuple[bool, str]:
    """Initialize config file with defaults.

    Returns:
        Tuple of (created: bool, message: str)
    """
    ensure_config_dir()

    if CONFIG_FILE.exists() and not overwrite:
        return False, f"Config already exists at {CONFIG_FILE}"

    CONFIG_FILE.write_text(get_default_config_toml())
    return True, f"Created config at {CONFIG_FILE}"
