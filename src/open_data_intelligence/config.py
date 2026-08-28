from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(value: str) -> str:
    """Select the installed psycopg v3 driver for provider-style PostgreSQL URLs."""
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Open Data Intelligence Pipeline")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = _normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite+pysqlite:///./open_data_intelligence.db")
    )
    auto_create_schema: bool = _as_bool(os.getenv("AUTO_CREATE_SCHEMA", "true"))
    prozorro_api_url: str = os.getenv(
        "PROZORRO_API_URL", "https://public-api.prozorro.gov.ua/api/2.5"
    )
    prozorro_timeout_seconds: float = float(os.getenv("PROZORRO_TIMEOUT_SECONDS", "15"))
    prozorro_max_retries: int = int(os.getenv("PROZORRO_MAX_RETRIES", "2"))


settings = Settings()
