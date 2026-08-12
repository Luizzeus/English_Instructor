from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "English Instructor API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # SQL Server
    database_url: str = "mssql+pyodbc://localhost/EnglishInstructor?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

    # Anthropic (conversation bot)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Azure AI Speech (STT + Pronunciation Assessment + TTS)
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_speech_language: str = "en-US"
    azure_tts_voice: str = "en-US-AriaNeural"

    # Clerk (auth)
    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    # Origins allowed to present a Clerk session token (checked against the `azp` claim)
    clerk_authorized_parties: list[str] = ["http://localhost:5173"]

    # Cost controls
    daily_session_limit_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
