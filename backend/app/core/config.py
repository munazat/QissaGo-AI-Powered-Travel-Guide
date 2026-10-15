"""All settings come from environment variables (or the .env file).

Copy `.env.example` to `.env` and change values there. Never commit `.env`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "QissaGo API"
    database_url: str = "postgresql+psycopg://qissago:qissago@localhost:5432/qissago"

    # Login tokens
    jwt_secret: str = "change-me-in-your-env-file-use-a-long-random-value"
    jwt_expire_hours: int = 72

    # Chatbot language model: "ollama" (free, runs on your laptop) or "none" (rules only)
    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    llm_timeout_seconds: float = 25.0

    # Live weather from Open-Meteo (free, no key). Set false to always use seasonal estimates.
    live_weather: bool = True

    # Which websites may call the API (Flutter web dev server, GitHub Pages ...). "*" = any.
    cors_origins: str = "*"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
