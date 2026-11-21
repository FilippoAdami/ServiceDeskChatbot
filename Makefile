.PHONY: help install test test-backend test-frontend lint type-check build check dev-backend dev-frontend

help:
	@echo "Service Desk AI Assistant — Commands:"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make test            Run backend and frontend tests"
	@echo "  make lint            Run ruff and eslint"
	@echo "  make type-check      Run mypy and tsc"
	@echo "  make build           Build production frontend bundle"
	@echo "  make check           Run all quality checks (tests, lint, typecheck, build)"
	@echo "  make dev-backend     Start FastAPI backend server on port 8000"
	@echo "  make dev-frontend    Start Vite frontend dev server on port 5173"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
	cd frontend && npm install

test-backend:
	PYTHONPATH=. .venv/bin/pytest backend/tests

test-frontend:
	cd frontend && npm test

migrate:
	.venv/bin/alembic upgrade head

test: test-backend test-frontend

lint:
	.venv/bin/ruff check backend
	cd frontend && npm run lint

type-check:
	.venv/bin/mypy backend
	cd frontend && npm run type-check

build:
	cd frontend && npm run build

check: test lint type-check build

dev-backend:
	.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

rag-index:
	.venv/bin/python backend/scripts/index_kb.py

rag-index-fake:
	.venv/bin/python backend/scripts/index_kb.py --fake-encoder

rag-eval:
	.venv/bin/python backend/scripts/evaluate_rag.py

rag-eval-offline:
	.venv/bin/python backend/scripts/evaluate_rag.py --fake-encoder
