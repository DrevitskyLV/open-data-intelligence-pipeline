.PHONY: install run test lint format migrate docker-up docker-down

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn open_data_intelligence.main:app --reload

test:
	pytest --cov=open_data_intelligence --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .
	mypy src

format:
	ruff check --fix .
	ruff format .

migrate:
	alembic upgrade head

docker-up:
	docker compose up --build

docker-down:
	docker compose down

