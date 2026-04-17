from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API
    app_name: str = "InferX"
    debug: bool = False

    # Backend selection: "openai" | "echo"
    # Set BACKEND_TYPE=echo to run without an API key (local dev / CI default).
    backend_type: str = "openai"

    # OpenAI — only required when backend_type == "openai"
    openai_api_key: str = "not-set"
    openai_base_url: str | None = None  # override for Together, Groq, etc.

    # Database
    database_url: str = "postgresql+asyncpg://inferx:inferx@localhost:5432/inferx"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    return Settings()
