from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCPILOT_", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql://docpilot:docpilot@localhost:5432/docpilot"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Ingestion
    max_upload_mb: int = 20
    chunk_max_chars: int = 1000
    chunk_overlap_chars: int = 150

    # Local embedding model (downloaded once, then cached)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    model_cache_dir: Path = Path.home() / ".cache" / "docpilot" / "models"


@lru_cache
def get_settings() -> Settings:
    return Settings()
