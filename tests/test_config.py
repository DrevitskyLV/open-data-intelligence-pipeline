from __future__ import annotations

import pytest

from open_data_intelligence.config import _normalize_database_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        (
            "postgres://app:secret@db.example.test/intelligence?sslmode=require",
            "postgresql+psycopg://app:secret@db.example.test/intelligence?sslmode=require",
        ),
        (
            "postgresql://app:secret@db.example.test/intelligence",
            "postgresql+psycopg://app:secret@db.example.test/intelligence",
        ),
        (
            "postgresql+psycopg://app:secret@db.example.test/intelligence",
            "postgresql+psycopg://app:secret@db.example.test/intelligence",
        ),
        (
            "sqlite+pysqlite:///./open_data_intelligence.db",
            "sqlite+pysqlite:///./open_data_intelligence.db",
        ),
    ],
)
def test_normalize_database_url(raw_url: str, expected: str) -> None:
    assert _normalize_database_url(raw_url) == expected
