.PHONY: up down restart logs migrate setup

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Restart all services
restart:
	docker compose down && docker compose up -d

# Follow logs
logs:
	docker compose logs -f

# Run database migrations
migrate:
	docker compose exec backend alembic upgrade head

# First-time setup: start services, wait for healthy backend, run migrations
setup:
	docker compose up -d
	@echo "Waiting for backend to be healthy..."
	@until docker compose exec backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; do sleep 2; done
	@echo "Running migrations..."
	docker compose exec backend alembic upgrade head
	@echo "Ready at http://localhost:3000"
