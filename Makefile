.PHONY: help up down restart logs build migrate seed simulate test test-backend lint clean

help:
	@echo "GuardRail - Fraud Alert Triage Console"
	@echo "======================================"
	@echo "make up            - Start all services with Docker Compose"
	@echo "make down          - Stop all Docker Compose services"
	@echo "make restart       - Restart Docker Compose services"
	@echo "make logs          - Tail Docker Compose logs"
	@echo "make build         - Build container images"
	@echo "make migrate       - Run database migrations"
	@echo "make seed          - Seed demo alerts and analysts"
	@echo "make simulate      - Run continuous transaction simulator"
	@echo "make test          - Run all test suites"
	@echo "make test-backend  - Run backend pytest suite"
	@echo "make clean         - Remove caches and build artifacts"

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python scripts/seed_data.py

simulate:
	docker compose exec backend python scripts/simulate_transactions.py

test: test-backend

test-backend:
	pytest backend/tests -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov frontend/dist
