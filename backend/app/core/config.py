from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "English Instructor API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # PostgreSQL (open-source, self-hosted — see docs/architecture.md section 1.1)
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/english_instructor"

    # LLM provider (conversation bot + metrics grading) — see docs/architecture.md
    # section 1.1. "ollama" (default) is local/open-weight/$0; "anthropic" is kept
    # as a swap-back option, not deleted, in case paid quality is worth it later.
    llm_provider: Literal["ollama", "anthropic"] = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    # Anthropic (conversation bot) — only used when llm_provider="anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Azure AI Speech (STT + Pronunciation Assessment + TTS)
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_speech_language: str = "en-US"
    azure_tts_voice: str = "en-US-AriaNeural"

    # Auth (self-hosted email/password — see docs/architecture.md section 1.1)
    secret_key: str = ""
    access_token_expire_minutes: int = 60 * 24 * 14  # 14 days

    # Cost controls
    daily_session_limit_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
