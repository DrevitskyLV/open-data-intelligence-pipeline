from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Open Data Intelligence Pipeline")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./open_data_intelligence.db")
    auto_create_schema: bool = _as_bool(os.getenv("AUTO_CREATE_SCHEMA", "true"))


settings = Settings()
