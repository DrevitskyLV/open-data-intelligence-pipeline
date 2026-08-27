# Open Data Intelligence Pipeline

Independent portfolio project demonstrating idempotent ingestion, entity normalization,
relationship discovery and explainable analytics over public-style procurement data.

The repository uses synthetic fixtures and does not contain commercial code, client data,
personal data or reverse-engineered company logic.

## Why this project exists

Real integration services must do more than expose CRUD endpoints. They need to validate
untrusted input, resolve repeated entities, survive reprocessing, explain analytical results
and expose observable synchronization state. This project packages those concerns into a
small system that can be reviewed and run locally.

```mermaid
flowchart TD
    A["Open-data connector or fixtures"] --> B["Validation and ingestion"]
    B --> C["Normalization and entity resolution"]
    C --> D["PostgreSQL"]
    D --> E["Explainable signal engine"]
    D --> F["FastAPI search and relationship API"]
```

## Current capabilities

- Validated ingestion from deterministic JSON fixtures.
- Idempotent upserts keyed by stable external identifiers.
- Organization resolution across differently formatted registration codes.
- Normalized organization names for search and later fuzzy matching.
- Explainable analytical signals:
  - short tender deadline;
  - high-value contract;
  - supplier concentration.
- Aggregated buyer/supplier relationships.
- Interactive dashboard for loading fixtures, searching entities and inspecting relationships.
- Search and filters through a documented REST API.
- PostgreSQL in Docker, SQLite for zero-configuration local development.
- Alembic migrations, pytest suite and GitHub Actions.

## Quick start with Docker

Requirements: Docker with Compose.

```bash
docker compose up --build
```

Open:

- Interactive dashboard: http://localhost:8000/dashboard
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

### One-click Windows preview

If Python 3.12 is installed, double-click `start_demo.bat`. The script creates a local virtual
environment on first launch, installs dependencies, starts the API and opens the interactive
dashboard in the default browser. Keep the terminal window open; press `Ctrl+C` to stop it.

Load the demo dataset:

```bash
curl -X POST http://localhost:8000/api/v1/sync-runs \
  -H "Content-Type: application/json" \
  -d '{"source":"fixtures"}'
```

Run the same request again: `records_created` becomes `0`, while the database still contains
six procurements. This demonstrates idempotent reprocessing.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
cp .env.example .env                   # optional; environment variables are read directly
uvicorn open_data_intelligence.main:app --reload
```

The default database is SQLite. For PostgreSQL, set `DATABASE_URL` and run:

```bash
alembic upgrade head
```

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/sync-runs` | Validate and ingest the fixture dataset |
| `GET` | `/api/v1/sync-runs/{id}` | Inspect synchronization status and counters |
| `GET` | `/api/v1/organizations` | Search organizations by name or code |
| `GET` | `/api/v1/organizations/{id}` | View organization summary |
| `GET` | `/api/v1/organizations/{id}/relationships` | Aggregate buyers and suppliers |
| `GET` | `/api/v1/procurements` | List normalized procurements |
| `GET` | `/api/v1/risk-signals` | Filter explainable analytical signals |

## Quality checks

```bash
pytest --cov=open_data_intelligence --cov-report=term-missing
ruff check .
ruff format --check .
mypy src
```

## Design decisions

### Stable identifiers before fuzzy matching

Registration codes are normalized first because deterministic evidence should have priority
over probabilistic name similarity. Fuzzy matching is listed as a later, reviewable layer.

### Explainable signals

Every signal contains a human-readable reason and links back to an organization or procurement.
The project deliberately avoids pretending that deterministic rules are an ML risk score.

### Synchronous v0.1 ingestion

The first release executes a small deterministic dataset inside the request so reviewers can
run the complete flow without operating a queue. The service boundary and `sync_runs` model are
already present; moving execution to a Redis-backed worker is the first roadmap milestone.

## Repository structure

```text
src/open_data_intelligence/
├── api.py                  # HTTP endpoints and query composition
├── config.py               # Environment-driven configuration
├── db.py                   # SQLAlchemy engine and session lifecycle
├── models.py               # Persistence model
├── schemas.py              # Input and output contracts
└── services/
    ├── ingestion.py        # Validation, entity upsert and idempotency
    ├── normalization.py    # Deterministic organization normalization
    └── signals.py          # Explainable analytical rules
```

See [docs/ROADMAP.md](docs/ROADMAP.md) for deliberately scoped next steps.
Use [docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) to prepare the technical explanation and
[docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) when publishing the repository.

## Author

Lev Drevytskyi — Python Backend Developer
