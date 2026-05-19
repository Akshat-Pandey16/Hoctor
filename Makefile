PYTHON ?= python
UV ?= uv
MANAGE = $(UV) run python manage.py
PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: help install sync upgrade env migrate makemigrations seed reset-db \
        run shell superuser collectstatic test cov lint fmt fmt-check check \
        precommit clean docker-build docker-up docker-down docker-logs \
        docker-shell schema all

help:
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "\033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

install: ## Install runtime + dev deps (one-time)
	$(UV) sync

sync: ## Install/refresh deps from lockfile
	$(UV) sync

upgrade: ## Upgrade all deps to latest within constraints
	$(UV) sync --upgrade

env: ## Copy .env.example -> .env if missing
	@test -f .env || cp .env.example .env

migrate: ## Apply database migrations
	$(MANAGE) migrate

makemigrations: ## Generate new migrations
	$(MANAGE) makemigrations

seed: ## Seed demo venues, rooms, and fingerprints
	$(MANAGE) seed_demo

reset-db: ## Drop and re-seed local sqlite DB
	rm -f db.sqlite3
	$(MAKE) migrate
	$(MANAGE) seed_demo --reset

run: ## Start the Django dev server on PORT (default 8000)
	$(MANAGE) runserver 0.0.0.0:$(PORT)

shell: ## Open a Django shell (ipython if installed)
	$(MANAGE) shell

superuser: ## Create a Django superuser
	$(MANAGE) createsuperuser

collectstatic: ## Collect static files for production
	$(MANAGE) collectstatic --noinput

schema: ## Dump the OpenAPI schema to schema.yml
	$(MANAGE) spectacular --file schema.yml --validate

test: ## Run pytest
	$(UV) run pytest

cov: ## Run tests with coverage report
	$(UV) run pytest --cov=hoctor --cov=config --cov-report=term-missing --cov-report=html

lint: ## Lint with ruff
	$(UV) run ruff check .

fmt: ## Auto-fix + format with ruff
	$(UV) run ruff check . --fix
	$(UV) run ruff format .

fmt-check: ## Check formatting without writing
	$(UV) run ruff format --check .

check: lint fmt-check test ## Run lint + format check + tests

precommit: ## Install + run pre-commit hooks
	$(UV) run pre-commit install
	$(UV) run pre-commit run --all-files

clean: ## Remove caches and build artifacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	rm -rf htmlcov .coverage build dist *.egg-info schema.yml

docker-build: ## Build production Docker image
	docker build -t hoctor:latest .

docker-up: ## Start Postgres + web container
	docker compose up --build -d

docker-down: ## Stop docker compose stack
	docker compose down

docker-logs: ## Tail web container logs
	docker compose logs -f web

docker-shell: ## Open a shell inside the running web container
	docker compose exec web bash

all: install env migrate seed run ## First-run: install, migrate, seed, then runserver
