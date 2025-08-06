# FuzeAgent Development Makefile
.PHONY: help dev prod build clean rebuild test logs status stop

# Default target
help: ## Show this help message
	@echo "🚀 FuzeAgent Development Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Start development environment with hot reload
	@echo "🚀 Starting development environment..."
	@./scripts/build-dev.sh

prod: ## Build and start production environment
	@echo "🏭 Starting production environment..."
	@./scripts/build-prod.sh
	@docker-compose up -d

build: ## Build all services (development)
	@echo "📦 Building all services..."
	@export DOCKER_BUILDKIT=1 && docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --parallel

rebuild: ## Rebuild all services without cache
	@echo "🔄 Rebuilding all services..."
	@export DOCKER_BUILDKIT=1 && docker-compose build --no-cache --parallel

clean: ## Clean up containers, images, and volumes
	@echo "🧹 Cleaning up..."
	@docker-compose down -v --remove-orphans
	@docker system prune -af
	@docker volume prune -f

test: ## Run tests
	@echo "🧪 Running tests..."
	@docker-compose exec orchestrator python -m pytest
	@docker-compose exec ui npm test

logs: ## Show logs for all services
	@docker-compose logs -f

status: ## Show status of all services
	@docker-compose ps

stop: ## Stop all services
	@docker-compose down

restart: ## Restart specific service (usage: make restart SERVICE=ui)
	@docker-compose restart $(SERVICE)

shell-ui: ## Open shell in UI container
	@docker-compose exec ui sh

shell-api: ## Open shell in orchestrator container
	@docker-compose exec orchestrator bash

# Quick service targets
ui: ## Rebuild and restart UI only
	@export DOCKER_BUILDKIT=1 && docker-compose build ui && docker-compose up -d ui

api: ## Rebuild and restart API services only
	@export DOCKER_BUILDKIT=1 && docker-compose build orchestrator hierarchy-api && docker-compose up -d orchestrator hierarchy-api