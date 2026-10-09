from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCPILOT_", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql://docpilot:docpilot@localhost:5432/docpilot"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
