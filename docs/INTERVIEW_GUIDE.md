# Interview guide

This file is a study guide, not a script to memorize word for word. Be ready to open the code
and explain every statement below.

## 90-second project explanation

I built an independent open-data pipeline to demonstrate the backend problems that are hidden
behind a simple API. The service validates procurement-style records, normalizes organization
identifiers and names, performs idempotent upserts, creates explainable analytical signals and
exposes relationships through FastAPI. PostgreSQL is used in the Docker environment, while
SQLite keeps local setup simple. Alembic manages the schema, and pytest, Ruff, mypy and GitHub
Actions provide automated quality checks. The optional Prozorro connector reads the official
descending feed, follows cursor-style pagination and concurrently loads tender details. It maps
only active awards and deliberately excludes public contact fields from persistence.

The live connector is async and includes timeouts, bounded concurrency and retries for rate limits
and transient server errors. It currently completes a small bounded sync inside the HTTP request;
my next production step would be moving that work to a Redis-backed worker and preserving raw
source documents in object storage.

## Code areas to understand

| Topic | File | What to explain |
| --- | --- | --- |
| Dependency injection | `api.py`, `db.py` | Why one SQLAlchemy session is scoped to one request |
| Validation | `schemas.py` | Why external input is parsed before persistence |
| External API | `connectors/prozorro.py` | Pagination, timeout, retries, mapping and data minimization |
| Idempotency | `services/ingestion.py` | Why stable `external_id` and registration codes prevent duplicates |
| Entity resolution | `services/normalization.py` | Deterministic matching first, fuzzy matching later |
| Analytics | `services/signals.py` | Why signals are explainable rules rather than an invented ML score |
| Data integrity | `models.py`, migration | Unique constraints, foreign keys and indexes |
| Testing | `tests/` | Difference between unit, service and HTTP tests |

## Questions you should be able to answer

### Why does ingestion still finish inside the request?

The requested batch is intentionally small and bounded, so request-scoped completion makes the
whole flow easy for a reviewer to run. The live HTTP calls themselves are asynchronous. The
`sync_runs` model and ingestion service boundary allow the same orchestration to be moved to a
worker without changing the public reporting model.

### Why are live API tests mocked?

An external dataset changes continuously and can be slow or temporarily unavailable. Connector
tests use an in-memory HTTP transport to prove pagination, retry and mapping behavior
deterministically. A separate manual smoke test verifies live compatibility without making CI
flaky.

### What happens if two workers ingest the same record at once?

The database unique constraint is the final protection. The current select-then-insert flow would
need `INSERT ... ON CONFLICT DO UPDATE` or IntegrityError retry handling before multiple workers
are enabled. Do not claim that v0.1 already solves concurrent upserts.

### Why not use fuzzy matching immediately?

Stable registration identifiers are stronger evidence. Fuzzy matching can create false positives,
so it should produce a confidence score and a review queue instead of silently merging records.

### Why are signals rebuilt?

The fixture dataset is tiny, and rebuilding makes derived data deterministic. At larger scale,
signals should be incrementally recalculated only for affected entities and periods.

### What would you monitor in production?

- synchronization duration and failure rate;
- source response latency and rate-limit events;
- records created, updated and rejected;
- queue depth and retry count;
- database query latency;
- signal counts by type and source version.

## Safe recruiter wording

This is an independent portfolio project inspired by common ingestion and open-data analysis
problems. It contains synthetic data and no code or information from my confidential commercial
project.
