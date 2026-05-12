"""
config.py
─────────
Application settings loaded from environment variables / .env file.
Using pydantic-settings gives us:
  • Automatic .env loading
  • Type coercion + validation at startup
  • A single import to access every env var
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Load .env from the repository root regardless of current working dir.
        # (Developers often run from `backend/` or repo root.)
        env_file=[
            str(Path(__file__).resolve().parents[1] / ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required ──────────────────────────────────────────────────────────────
    sunbird_api_token: str = Field(
        ...,
        description="Bearer token for the Sunbird AI API.",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # In production set this to your exact frontend URL.
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated CORS allowed origins.",
    )

    # ── App meta ──────────────────────────────────────────────────────────────
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    @field_validator("sunbird_api_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SUNBIRD_API_TOKEN must not be empty.")
        return v.strip()

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()  # type: ignore[call-arg]