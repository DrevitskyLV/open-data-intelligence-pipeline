# Roadmap

The first release intentionally focuses on a reliable, demonstrable vertical slice.

## Implemented in v0.1

- FastAPI REST API and OpenAPI documentation.
- PostgreSQL production configuration and SQLite developer fallback.
- Alembic initial migration.
- Fixture connector with Pydantic validation.
- Organization normalization and registration-code entity resolution.
- Idempotent procurement upserts.
- Explainable short-deadline, high-value and supplier-concentration signals.
- Relationship aggregation API.
- Unit and API tests.
- Docker Compose and GitHub Actions.

## Next milestones

1. Move ingestion to a Redis-backed worker and return `queued` immediately.
2. Add a real public-data connector with pagination, timeouts and exponential backoff.
3. Preserve raw source documents in object storage.
4. Add fuzzy entity matching with reviewable match confidence.
5. Add cursor pagination and full-text search.
6. Add Prometheus metrics and structured JSON logs.
7. Add a small graph visualization client.

