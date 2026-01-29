.PHONY: help build up down restart logs logs-api logs-worker logs-redis logs-mongo clean test health crawl

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d
	@echo "Services started!"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "MongoDB: localhost:27017"
	@echo "Redis: localhost:6379"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show API logs
	docker compose logs -f api

logs-worker: ## Show worker logs
	docker compose logs -f worker

logs-redis: ## Show Redis logs
	docker compose logs -f redis

logs-mongo: ## Show MongoDB logs
	docker compose logs -f mongodb

clean: ## Stop services and remove volumes
	docker compose down -v
	@echo "Cleaned up containers and volumes"

health: ## Check health of all services
	@echo "Checking API health..."
	curl -s http://localhost:8000/health | python3 -m json.tool

ping: ## Lightweight API ping (no DB or worker checks)
	@echo "Pinging API..."
	@curl -s http://localhost:8000/ping | python3 -m json.tool || echo "❌ API ping failed"

stats: ## Get crawler statistics
	@echo "Fetching crawler statistics..."
	curl -s http://localhost:8000/stats | python3 -m json.tool

scale-workers: ## Scale workers (usage: make scale-workers N=4)
	docker compose up -d --scale worker=$(N)
	@echo "Scaled workers to $(N) instances"

shell-mongo: ## Open MongoDB shell
	docker exec -it crawler-mongodb mongosh web_crawler

shell-redis: ## Open Redis CLI
	docker exec -it crawler-redis redis-cli

install: ## Install Python dependencies locally
	pip install -r requirements.txt

dev-api: ## Run API locally (for development)
	cd src && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: ## Run Celery worker locally (for development)
	cd src && celery -A worker.tasks worker --loglevel=info --concurrency=4

test: ## Run integration tests
	./run_tests.sh

test-quick: ## Run quick health check
	@echo "Quick health check..."
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ API not responding"
	@echo ""

