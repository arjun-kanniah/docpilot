from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The project's .env, wherever the process starts. Real environment variables take precedence.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or the project's .env file."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="DOCPILOT_", extra="ignore")

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

    # Answering: defaults for POST /api/ask; a request can pick another allowlisted model
    llm_provider: str = "anthropic"
    llm_model: str | None = None  # None means the provider's default model
    answer_top_k: int = 6
    answer_max_tokens: int = 16000

    # Agent mode: POST /api/agent
    agent_max_rounds: int = 2  # research rounds, including ones the analyst asks for
    agent_max_tool_calls: int = 6  # per round
    agent_search_k: int = 5  # passages per search
    agent_question_cost: int = 5  # an agent run counts as this many questions on the demo

    # Provider keys use the SDKs' standard names, without the DOCPILOT_ prefix
    anthropic_api_key: SecretStr = Field(SecretStr(""), validation_alias="ANTHROPIC_API_KEY")
    gemini_api_key: SecretStr = Field(SecretStr(""), validation_alias="GEMINI_API_KEY")
    openai_api_key: SecretStr = Field(SecretStr(""), validation_alias="OPENAI_API_KEY")

    # Public demo: read-only library, a narrower model list, and question limits
    demo_mode: bool = False
    allowed_models: list[str] | None = None  # e.g. '["claude-haiku-5-5"]'; None allows all
    demo_questions_per_hour: int = 20  # per visitor
    demo_questions_per_day: int = 500  # per running instance
    # Shared with the Cloudflare Worker in front of the demo, which passes on the visitor's IP
    proxy_secret: SecretStr = SecretStr("")

    # Built web app to serve from the API (set in the production image)
    static_dir: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
