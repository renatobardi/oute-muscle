.PHONY: help install dev test test-unit test-cov lint type-check format clean

# ── Colours ────────────────────────────────────────────────────────────────
RESET  := \033[0m
BOLD   := \033[1m
GREEN  := \033[32m
YELLOW := \033[33m

help: ## Show this help
	@echo "$(BOLD)Oute Muscle — available commands$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-18s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Setup ──────────────────────────────────────────────────────────────────
install: ## Install all dependencies (Python + Node)
	uv sync --all-packages --group dev
	cd apps/web && npm install

# ── Development ────────────────────────────────────────────────────────────
dev: ## Start FastAPI dev server
	uvicorn apps.api.src.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Start SvelteKit dev server
	cd apps/web && npm run dev

# ── Tests ──────────────────────────────────────────────────────────────────
test: ## Run all backend tests
	pytest

test-unit: ## Run unit tests only
	pytest apps/api/tests/unit/ packages/core/tests/

test-cov: ## Run tests with coverage report
	pytest --cov --cov-report=term-missing --cov-report=html

test-rules: ## Run Semgrep rule tests
	semgrep --test packages/semgrep-rules/

test-web: ## Run frontend unit tests
	cd apps/web && npx vitest run

test-e2e: ## Run Playwright e2e tests
	cd apps/web && npx playwright test

# ── Quality ────────────────────────────────────────────────────────────────
lint: ## Run all linters (Python + frontend)
	ruff check .
	cd apps/web && npx eslint .

type-check: ## Run type checkers (mypy + svelte-check)
	mypy --strict packages/core/
	cd apps/web && npm run check

format: ## Auto-format code
	ruff format .
	cd apps/web && npx prettier --write .

# ── Migrations ─────────────────────────────────────────────────────────────
migrate-up: ## Apply pending migrations
	alembic -c packages/db/alembic.ini upgrade head

migrate-down: ## Rollback last migration
	alembic -c packages/db/alembic.ini downgrade -1

migrate-gen: ## Generate new migration (use: make migrate-gen MSG="description")
	alembic -c packages/db/alembic.ini revision --autogenerate -m "$(MSG)"

# ── Cleanup ────────────────────────────────────────────────────────────────
clean: ## Remove build and cache artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
