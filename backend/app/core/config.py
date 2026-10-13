"""
Application configuration via pydantic-settings.
Values are loaded from environment variables or a .env file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────
    app_name: str = "CYBER-20 Federated Threat Detection"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # ── Server ─────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Database ───────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./cyber20.db"

    # ── CORS ───────────────────────────────────────────────
    cors_origins: str = (
        "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173"
    )

    # ── Logging ────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Computed ───────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
