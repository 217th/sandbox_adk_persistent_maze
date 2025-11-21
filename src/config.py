"""
Configuration load/validation via pydantic-settings.

What it does:
- Reads required env: GOOGLE_APPLICATION_CREDENTIALS (FilePath), FIRESTORE_PROJECT_ID, MAZE_COLLECTION_NAME.
- Reads optional env: LOG_LEVEL (default INFO), GOOGLE_API_KEY, VERTEXAI_PROJECT, VERTEXAI_LOCATION.
- Loads .env by default; extra keys are ignored.
- Raises on invalid/missing required values (fail-fast at startup).

Usage:
- load_config() returns a validated AppConfig instance.
"""

from typing import Optional

from pydantic import Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Validated environment configuration."""

    GOOGLE_APPLICATION_CREDENTIALS: FilePath
    FIRESTORE_PROJECT_ID: str
    MAZE_COLLECTION_NAME: str
    LOG_LEVEL: str = Field(default="INFO")
    GOOGLE_API_KEY: Optional[str] = None
    VERTEXAI_PROJECT: Optional[str] = None
    VERTEXAI_LOCATION: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def load_config() -> AppConfig:
    """Load and validate configuration, raising on error."""
    return AppConfig()
