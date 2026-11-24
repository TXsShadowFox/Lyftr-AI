SHELL := /bin/sh
.DEFAULT_GOAL := help

.PHONY: help env up down logs ps build test test-backend test-frontend clean

help: ## Show available commands
	@echo "LYFTR AI"
	@echo ""
	@echo "  make env             Create .env from .env.example if missing"
	@echo "  make up              Build and start frontend + backend"
	@echo "  make down            Stop the stack (keeps the SQLite volume)"
	@echo "  make logs            Follow container logs"
	@echo "  make ps              Show container status"
	@echo "  make build           Build both images"
	@echo "  make test            Run backend tests and frontend typecheck/build"
	@echo "  make test-backend    Run pytest"
	@echo "  make test-frontend   Run TypeScript + Vite production build"
	@echo "  make clean           Stop the stack and delete the SQLite volume"
	@echo ""
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example. Add real LLM_API_KEYS before chatting."; \
	fi

up: env ## Build and start the complete stack
	docker compose up --build -d
	@echo ""
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	@echo "Status:   docker compose ps"

down: ## Stop the stack, preserving the SQLite volume
	docker compose down

logs: ## Follow container logs
	docker compose logs -f --tail=100

ps: ## Show container status
	docker compose ps

build: ## Build both images
	docker compose build

test-backend: ## Run the backend test suite
	cd backend && python -m pytest -q

test-frontend: ## Typecheck and build the frontend
	cd frontend && npm run build

test: test-backend test-frontend ## Run all automated checks

clean: ## Stop the stack and delete persisted data
	docker compose down -v
