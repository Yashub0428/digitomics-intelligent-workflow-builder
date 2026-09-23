from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and optional .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "digitomics-workflow-builder"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "sqlite:///./app.db"

    llm_provider: str = "gemini"
    llm_model: str = "gemini-3-flash-preview"
    llm_timeout_ms: int = 15000
    llm_thinking_budget: int | None = 0
    gemini_api_key: str | None = None

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
